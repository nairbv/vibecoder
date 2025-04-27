import time

class AgentStatus:
    def status_line(self):
        raise NotImplementedError("Must be implemented in subclasses")

    def is_busy(self):
        return False

class WorkingStatus(AgentStatus):
    def __init__(self, duration):
        self.start_time = time.time()
        self.end_time = self.start_time + duration

    def status_line(self):
        remaining = max(0, self.end_time - time.time())
        minutes, seconds = divmod(remaining, 60)
        time_display = f"⏳ {minutes:.0f}:{seconds:02.0f} remaining"
        return f"⚡ Working {time_display}"

    def is_busy(self):
        return True

class WaitingStatus(AgentStatus):
    def status_line(self):
        return "👂 Waiting for input..."

class RespondingStatus(AgentStatus):
    def status_line(self):
        return "💭 Responding..."

    def is_busy(self):
        return True
