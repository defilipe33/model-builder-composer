import re
from dataclasses import dataclass

@dataclass
class Condition:
    field: str
    operator: str
    value: object

@dataclass
class Binary:
    operator: str
    left: object
    right: object

TOKEN = re.compile(
    r'''\s*(?:(\[[^\]]+\])|('(?:''|[^'])*')|("(?:""|[^"])*")|(>=|<=|!=|<>|=|>|<)|\b(AND|OR|LIKE)\b|([()])|([^\s()]+))''',
    re.I,
)

def tokenize(text):
    out=[]; pos=0
    while pos < len(text):
        m=TOKEN.match(text,pos)
        if not m:
            raise ValueError("Não foi possível interpretar a expressão.")
        pos=m.end()
        bracket,sq,dq,op,word,paren,bare=m.groups()
        if bracket: out.append(("FIELD", bracket[1:-1]))
        elif sq: out.append(("VALUE", sq[1:-1].replace("''","'")))
        elif dq: out.append(("VALUE", dq[1:-1].replace('""','"')))
        elif op: out.append(("OP", "!=" if op=="<>" else op))
        elif word:
            u=word.upper(); out.append((u,u))
        elif paren: out.append((paren,paren))
        elif bare: out.append(("BARE",bare))
    return out

def cast_value(v):
    if not isinstance(v,str): return v
    low=v.casefold()
    if low=="true": return True
    if low=="false": return False
    if low in {"null","none"}: return None
    try: return int(v)
    except ValueError: pass
    try: return float(v)
    except ValueError: return v

class Parser:
    def __init__(self,text):
        self.t=tokenize(text); self.i=0
    def peek(self,*k):
        return self.i < len(self.t) and self.t[self.i][0] in k
    def take(self,*k):
        if not self.peek(*k):
            got=self.t[self.i][1] if self.i < len(self.t) else "fim"
            raise ValueError(f"Expressão inválida próximo de {got!r}.")
        x=self.t[self.i]; self.i+=1; return x
    def parse(self):
        if not self.t: raise ValueError("Escreva uma expressão.")
        n=self.parse_or()
        if self.i != len(self.t): raise ValueError("Há texto não reconhecido no final da expressão.")
        return n
    def parse_or(self):
        n=self.parse_and()
        while self.peek("OR"):
            self.take("OR"); n=Binary("OR",n,self.parse_and())
        return n
    def parse_and(self):
        n=self.factor()
        while self.peek("AND"):
            self.take("AND"); n=Binary("AND",n,self.factor())
        return n
    def factor(self):
        if self.peek("("):
            self.take("("); n=self.parse_or(); self.take(")"); return n
        return self.condition()
    def condition(self):
        field=self.take("FIELD","BARE")[1]
        if self.peek("LIKE"):
            self.take("LIKE"); op="LIKE"
        else:
            op=self.take("OP")[1]
        raw=self.take("VALUE","BARE")[1]
        return Condition(field,op,cast_value(raw))

def parse_expression(text):
    return Parser(text).parse()
