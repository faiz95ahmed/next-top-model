from entities.common import CommonObject
from typing import Dict, Union, List
import torch
import os
from datetime import datetime
import json

class ModelGroup(CommonObject):
    def __init__(self, name: str, desc: str, path: str, parent_project):
        super().__init__(name, desc)
        self.model_subgroups = {}
        self.path = path
        self.parent_project = parent_project

    def new_model_subgroup(self, name: str, desc: str):
        with self._lock:
            if name not in self.model_subgroups.keys():
                self.model_subgroups[self._autokey] = ModelSubgroup(name, desc, self)
                self._autokey += 1
            else:
                print("Model Subgroup already exists!")

class ModelSubgroup(CommonObject):
    def __init__(self, name: str, desc: str, parent_group):
        super().__init__(name, desc)
        self.models = {}
        self.parent_group = parent_group

    def new_model(self, name: str, desc: str,
                  hyperparameters: Dict[str, Union[str, int, float, bool]],
                  checkpoint_nums: List[int],
                  from_model: str):
        with self._lock:
            if name not in self.models.keys():
                self.models[self._autokey] = Model(name, desc, hyperparameters, checkpoint_nums, from_model, self)
                self._autokey += 1
            else:
                print("Model already exists!")

class Model(CommonObject):
    def __init__(self, name: str, desc: str,
                 hyperparameters: Dict[str, Union[str, int, float, bool]],
                 checkpoint_nums: List[int],
                 from_model: str,
                 parent_subgroup):
        super().__init__(name, desc)
        self.checkpoints = {}
        self.checkpoint_nums = checkpoint_nums
        self.from_model = from_model
        self.parent_subgroup = parent_subgroup
        self.make_directory()
        with open("{}/hyperparams.json".format(self.path), "w") as f:
            f.write(json.dumps(hyperparameters, indent=4, sort_keys=True))

    def new_checkpoint(self, checkpoint_num: int, save_path, loss):
        with self._lock:
            if checkpoint_num not in self.models.keys():
                path = "{}/{}_{}.pt".format(self.path, self.name, checkpoint_num)
                torch.save({
                    'checkpoint_num': checkpoint_num,
                    'model_state_dict': model_state_dict,
                    'optimizer_state_dict': optimizer_state_dict,
                    'loss': loss,
                    }, path)
                self.checkpoints[checkpoint_num] = Checkpoint(checkpoint_num, path, loss, self)
            else:
                print("Checkpoint already exists!")
    
    def make_directory(self):
        project_path = self.parent_subgroup.parent_group.parent_project.path
        project_name = self.parent_subgroup.parent_group.parent_project.name 
        model_group_name = self.parent_subgroup.parent_group.name
        model_subgroup_name = self.parent_subgroup.name
        model_name = self.name
        self.path = "{}/{}/{}/{}/{}".format(project_path, project_name, model_group_name, model_subgroup_name, model_name)
        os.makedirs(self.path, exist_ok=True)

class Checkpoint(CommonObject):
    def __init__(self, checkpoint_num: int, path: str, loss, parent_model):
        self.parent_model = parent_model
        self.checkpoint_num = checkpoint_num
        self.loss = loss
        self.path = path
        self.date = datetime.now()
        parent_model_name = self.parent_model.name
        super().__init__(parent_model_name + "_" + str(checkpoint_num), str(self.date))