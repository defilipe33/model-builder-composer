ACTIVE={'Pipe':'BaseLink_HMIActiveTopology_Data','Junction':'BaseIdahoNode_HMIActiveTopology_Data','Reservoir':'BaseIdahoNode_HMIActiveTopology_Data','Air Valve':'BaseIdahoNode_HMIActiveTopology_Data','Hydrant':'BaseIdahoNode_HMIActiveTopology_Data','Tank':'BaseIdahoNode_HMIActiveTopology_Data','Conventional Tank':'BaseIdahoNode_HMIActiveTopology_Data','TCV':'BaseDirectedNode_HMIActiveTopology_Data','FCV':'BaseDirectedNode_HMIActiveTopology_Data','PRV':'BaseDirectedNode_HMIActiveTopology_Data','PBV':'BaseDirectedNode_HMIActiveTopology_Data','Check Valve':'BaseDirectedNode_HMIActiveTopology_Data','Standard Pump':'BaseDirectedNode_HMIActiveTopology_Data','Variable Speed Pump Battery':'BaseDirectedNode_HMIActiveTopology_Data','Customer Meter':'CustomerNode_HMIActiveTopology_Data'}
PHYS={'Pipe':['BaseLink_Physical_Data','IdahoPipe_Physical_Data'],'Junction':['BaseIdahoNode_Physical_Data','IdahoJunction_Physical_Data'],'Reservoir':['BaseIdahoNode_Physical_Data','IdahoReservoir_Physical_Data'],'Air Valve':['BaseIdahoNode_Physical_Data','AirValve_Physical_Data'],'Hydrant':['BaseIdahoNode_Physical_Data','IdahoHydrant_Physical_Data'],'Tank':['BaseIdahoNode_Physical_Data','BaseTank_Physical_Data','IdahoTank_Physical_Data'],'Conventional Tank':['BaseIdahoNode_Physical_Data','BaseTank_Physical_Data','IdahoTank_Physical_Data','ConventionalTank_Physical_Data'],'TCV':['BaseDirectedNode_Physical_Data','BaseValve_Physical_Data','TCV_Physical_Data'],'FCV':['BaseDirectedNode_Physical_Data','BaseValve_Physical_Data','PressureValve_Physical_Data','FCV_Physical_Data'],'PRV':['BaseDirectedNode_Physical_Data','BaseValve_Physical_Data','PressureValve_Physical_Data','PRV_Physical_Data'],'PBV':['BaseDirectedNode_Physical_Data','BaseValve_Physical_Data','PBV_Physical_Data'],'Check Valve':['BaseDirectedNode_Physical_Data','CheckValve_Physical_Data'],'Standard Pump':['BaseDirectedNode_Physical_Data','BasePump_Physical_Data','StandardPump_Physical_Data'],'Variable Speed Pump Battery':['BaseDirectedNode_Physical_Data','VariableSpeedPumpBattery_Physical_Data'],'Customer Meter':['CustomerNode_Physical_Data']}
UDX={'Pipe':'IdahoPipe_HMIUserDefinedExtensions_Data','Junction':'IdahoJunction_HMIUserDefinedExtensions_Data','Reservoir':'IdahoReservoir_HMIUserDefinedExtensions_Data','Air Valve':'AirValve_HMIUserDefinedExtensions_Data','Hydrant':'IdahoHydrant_HMIUserDefinedExtensions_Data','Tank':'IdahoTank_HMIUserDefinedExtensions_Data','Conventional Tank':'ConventionalTank_HMIUserDefinedExtensions_Data','TCV':'TCV_HMIUserDefinedExtensions_Data','FCV':'FCV_HMIUserDefinedExtensions_Data','PRV':'PRV_HMIUserDefinedExtensions_Data','PBV':'PBV_HMIUserDefinedExtensions_Data','Check Valve':'CheckValve_HMIUserDefinedExtensions_Data','Standard Pump':'StandardPump_HMIUserDefinedExtensions_Data','Variable Speed Pump Battery':'VariableSpeedPumpBattery_HMIUserDefinedExtensions_Data','Customer Meter':'CustomerNode_HMIUserDefinedExtensions_Data'}
class QueryRepository:
    def __init__(self,m): self.model=m; self.schema=m.schema; self.resolver=m.resolver; self.context=m.context
    @staticmethod
    def cmp(a,op,b):
        import math

        if op=='contains':
            return a is not None and str(b).lower() in str(a).lower()
        if op=='startswith':
            return a is not None and str(a).lower().startswith(str(b).lower())
        if op=='endswith':
            return a is not None and str(a).lower().endswith(str(b).lower())

        if a is None:
            return op == 'ne' and b is not None

        # Equality should be numeric whenever both sides can be interpreted
        # as numbers. This is especially important after SI <-> internal
        # WaterGEMS unit conversion, where binary floating-point values may
        # differ by a tiny amount even though they represent the same value.
        if op in {'eq', 'ne'}:
            try:
                af = float(a)
                bf = float(b)
            except (TypeError, ValueError):
                equal = (a == b)
            else:
                equal = math.isclose(
                    af,
                    bf,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
            return equal if op == 'eq' else not equal

        try:
            af = float(a)
            bf = float(b)
        except (TypeError, ValueError):
            return False

        return {
            'gt': af > bf,
            'gte': af >= bf,
            'lt': af < bf,
            'lte': af <= bf,
        }[op]
    def filter_active(self,t,expected):
        out=[]
        for eid in self.model.root_ids(t):
            row,_,_=self.resolver.resolve_row(ACTIVE[t],eid,3,self.context); v=None if row is None or row['HMIActiveTopologyIsActive'] is None else bool(row['HMIActiveTopologyIsActive'])
            if v==expected: out.append(eid)
        return out
    def filter_dynamic(self,t,ns,field,op,expected):
        tables=PHYS[t] if ns=='physical' else ([UDX.get(t)] if ns=='udx' and UDX.get(t) else []); alt=4 if ns=='physical' else 100
        out=[]
        for eid in self.model.root_ids(t):
            actual=None
            for table in tables:
                if not table or not self.schema.table_exists(table):continue
                data,_,_=self.resolver.resolve_dict(table,eid,alt,self.context)
                if data.get(field) is not None: actual=data[field]
            if self.cmp(actual,op,expected):out.append(eid)
        return out
