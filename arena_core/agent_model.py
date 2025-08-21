# agent_model.py — defines Agent class independently
class Agent:
    def __init__(self, name, path, score=0, parent=None):
        self.name = name
        self.path = path
        self.score = score
        self.last_rc = None
        self.last_out = ""
        self.last_err = ""
        self.parent = parent
        self.mutation_desc = ""

    def __repr__(self):
        return f"<Agent {self.name} score={self.score}>"