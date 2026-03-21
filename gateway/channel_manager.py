class ChannelManager:
    def __init__(self):
        self.channels = {}
        
    def register(self, name, adapter):
        self.channels[name] = adapter
        
    def get(self, name):
        return self.channels.get(name)
