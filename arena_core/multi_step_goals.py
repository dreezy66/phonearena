# multi_step_goals.py — enables agents to define and execute sequential goal chains
import time
from arena_core.agent_runtime import get_agents, save_agents
from arena_core.agent_iq import compute_iq

class GoalStep:
    def __init__(self, description, action_func, dependencies=None):
        self.description = description
        self.action_func = action_func
        self.dependencies = dependencies or []
        self.completed = False

class GoalWorkflow:
    def __init__(self, agent):
        self.agent = agent
        self.steps = []

    def add_step(self, description, action_func, dependencies=None):
        self.steps.append(GoalStep(description, action_func, dependencies))

    def execute(self):
        print(f"[Workflow] Executing workflow for {self.agent.name}")
        for step in self.steps:
            if step.completed:
                continue
            # Check dependencies
            if any(not dep.completed for dep in (step.dependencies or [])):
                continue
            try:
                print(f"  -> Step: {step.description}")
                step.action_func(self.agent)
                step.completed = True
            except Exception as e:
                print(f"  [Workflow] Step failed: {e}")
        # Update agent IQ after workflow
        self.agent.iq = compute_iq(self.agent)
        return all(s.completed for s in self.steps)

def execute_all_workflows():
    agents = get_agents()
    for agent in agents:
        wf = getattr(agent, "workflow", None)
        if wf:
            wf.execute()
    save_agents(agents)
