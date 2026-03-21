class SessionManager:
    def __init__(self):
        self.sessions = {}
        
    def get_session(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        return self.sessions[session_id]
        
    def update_session(self, session_id, data):
        session = self.get_session(session_id)
        session.update(data)
        return session
