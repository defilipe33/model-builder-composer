from extractors.pipe import PipeExtractor
from extractors.node import NodeExtractor, NODE_CONFIGS
from extractors.tank import TankExtractor
from extractors.directed import DirectedNodeExtractor, DIRECTED_CONFIGS
from extractors.customer_meter import CustomerMeterExtractor
class ExtractionService:
    def __init__(self,db,schema,common,readers,context): self.db=db; self.schema=schema; self.common=common; self.readers=readers; self.context=context
    def extract_selected(self,selected):
        args=(self.db,self.schema,self.common,self.readers,self.context); groups={}
        if selected.get('Pipe'):
            vals,_=PipeExtractor(*args).extract_all(); groups['Pipe']=[e for e in vals if e.id in selected['Pipe']]
        node_names={c['type'] for c in NODE_CONFIGS}; chosen=node_names & set(selected)
        if chosen:
            gs,_=NodeExtractor(*args).extract_all()
            for n in chosen: groups[n]=[e for e in gs.get(n,[]) if e.id in selected[n]]
        chosen={'Tank','Conventional Tank'} & set(selected)
        if chosen:
            gs,_=TankExtractor(*args).extract_all()
            for n in chosen: groups[n]=[e for e in gs.get(n,[]) if e.id in selected[n]]
        dir_names={c[0] for c in DIRECTED_CONFIGS}; chosen=dir_names & set(selected)
        if chosen:
            gs,_=DirectedNodeExtractor(*args).extract_all()
            for n in chosen: groups[n]=[e for e in gs.get(n,[]) if e.id in selected[n]]
        if selected.get('Customer Meter'):
            vals,_=CustomerMeterExtractor(*args).extract_all()
            groups['Customer Meter']=[e for e in vals if e.id in selected['Customer Meter']]
        node_lookup={}
        for els in groups.values():
            for e in els:
                if hasattr(e,'x_ft'): node_lookup[e.id]=(e.label,e.element_type)
        for p in groups.get('Pipe',[]):
            p.start_node_label,p.start_node_type=node_lookup.get(p.start_node_id,(self.common.label(p.start_node_id) if p.start_node_id else '','Not loaded'))
            p.end_node_label,p.end_node_type=node_lookup.get(p.end_node_id,(self.common.label(p.end_node_id) if p.end_node_id else '','Not loaded'))
        return groups
