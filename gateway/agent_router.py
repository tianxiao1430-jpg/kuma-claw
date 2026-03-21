class AgentRouter:
    def __init__(self):
        self.routes = {}
        
    def register_route(self, pattern, target_agent):
        self.routes[pattern] = target_agent
        
    def route(self, message):
        return "default_agent"
