from entities.model import Model
class Job():
    def __init__(self, model: Model, device: int, checkpoint_start: int):
        self.model = model
        self.device = device
        self.checkpoint_start = checkpoint_start
        self.active = False

    def start(self):
        pass

    def pause(self):
        pass
    
        