
from pyomo.environ import *

class EnergyOptimizer:
    def __init__(self, scenario):
        self.data = scenario
        self.model = ConcreteModel()
        self.T = range(len(self.data["load"]))
        self.setup_model()

    def setup_model(self):
        m = self.model
        T = self.T
        data = self.data

        # Sets
        m.T = Set(initialize=T)

        # Parameters
        m.load = Param(m.T, initialize={t: data["load"][t] for t in T})
        m.pv = Param(m.T, initialize={t: data["pv"][t] for t in T})
        m.price = Param(m.T, initialize={t: data["price"][t] for t in T})
        m.battery_capacity = Param(initialize=data["battery_capacity"])
        m.battery_power = Param(initialize=data["battery_power"])
        m.eta_ch = Param(initialize=data.get("eta_ch", 0.95))
        m.eta_dis = Param(initialize=data.get("eta_dis", 0.95))

        # Variables
        m.charge = Var(m.T, domain=NonNegativeReals)
        m.discharge = Var(m.T, domain=NonNegativeReals)
        m.soc = Var(m.T, domain=NonNegativeReals)

        # Objective: Minimize energy cost
        def objective_rule(m):
            return sum((m.load[t] - m.pv[t] + m.charge[t] - m.discharge[t]) * m.price[t] for t in m.T)
        m.objective = Objective(rule=objective_rule, sense=minimize)

        # Constraints
        def soc_balance(m, t):
            if t == 0:
                return m.soc[t] == 0
            return m.soc[t] == m.soc[t-1] + m.charge[t-1]*m.eta_ch - m.discharge[t-1]/m.eta_dis
        m.soc_balance = Constraint(m.T, rule=soc_balance)

        def soc_limit(m, t):
            return m.soc[t] <= m.battery_capacity
        m.soc_limit = Constraint(m.T, rule=soc_limit)

        def charge_limit(m, t):
            return m.charge[t] <= m.battery_power
        m.charge_limit = Constraint(m.T, rule=charge_limit)

        def discharge_limit(m, t):
            return m.discharge[t] <= m.battery_power
        m.discharge_limit = Constraint(m.T, rule=discharge_limit)

    def solve(self, solver="glpk"):
        solver = SolverFactory(solver)
        result = solver.solve(self.model)
        return result
