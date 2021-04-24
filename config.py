import inspect
from functools import partial

import torch, torch.nn as nn



class Config:
    def __init__(self, cls, freeze=False, **kwargs):
        self.cls = cls
        self.isfrozen = False
        freeze = kwargs.pop('freeze', freeze)            
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.freeze(freeze)
        
    def __setattr__(self, key, value):
        if hasattr(self, 'isfrozen') and self.isfrozen and not hasattr(self, key):
            raise Exception('Config object has no attribute named:', key)
        super().__setattr__(key, value)
        
    def setattrs(self, kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)
        
    def freeze(self, frozen=True):
        self.isfrozen = frozen
        
    def create_object(self):
        if not hasattr(self, 'cls'):
            raise Exception(self, 'has not attribute cls')
        if not hasattr(self.cls, 'from_config'):
            raise Exception(self.cls, 'object has no attribute from_config')
        return self.cls.from_config(self)
    
    def __str__(self, prefix=''):
        result = ''
        for k, v in self.__dict__.items():
            if k == 'isfrozen':
                continue
            if isinstance(v, Config):
                result += prefix + k + ' : ' + '\n' + v.__str__(prefix=prefix+'    ')
            else:im
                result += prefix + k + ' : ' + str(v) + '\n'
        return result
    
    def __repr__(self, prefix=''):
        result = ''
        for k, v in self.__dict__.items():
            if k == 'isfrozen':
                continue
            if isinstance(v, Config):
                result += prefix + k + ' : ' + '\n' + v.__repr__(prefix=prefix+'    ')
            else:
                result += prefix + k + ' : ' + repr(v) + '\n'
        return result  
    

class ConfigList(Config):
    def __init__(self, configs=[]):
        self.cls = type(self)
        for c in configs:
            assert isinstance(c, Config)
        self.configs = configs
        self.freeze()
        
    def create_object(self):
        _torch = True
        models = []
        for c in self.configs:
            m = c.create_object()
            if not isinstance(m, nn.Module):
                _torch = False
            models.append(m)
        if _torch:
            models = nn.ModuleList(models)
        return model
        
        
class ConfigDict(Config):
    def __init__(self, configs={}):
        self.cls = type(self)
        for k, v in configs.items():
            assert isinstance(v, Config)
        self.configs = configs
        self.freeze()
        
    def create_object(self):
        _torch = True
        models = []
        for k, v in self.configs.items():
            m = v.create_object()
            if not isinstance(m, nn.Module):
                _torch = False
            models[k] = m
        if _torch:
            models = nn.ModuleDict(models)
        return model
    
    
    
    
    
def configurable(**kwargs):
    return partial(_configurable, **kwargs)
    
    
def _configurable(cls, **kwargs):
    def _get_config(m):
        if hasattr(m, 'current_config'):
            return m.current_config()
        elif isinstance(m, list) or isinstance(m, tuple) or isinstance(m, nn.ModuleList):
            cfgs = []
            for _m in m:
                _c = _get_config(_m)
                if _c is None:
                    return None
                cfgs.append(_c)
            return ConfigList(cfgs)
        elif isinstance(m, dict) or isinstance(m, nn.ModuleDict):
            cfgs = {}
            for _k, _m in m.items():
                _c = _get_config(_m)
                if _c is None:
                    return None
                cfgs[_k] = _c
            return ConfigDict(cfgs)
        else:
            return None                
    
    init_args = inspect.getfullargspec(cls.__init__)
    init_arg_names = init_args.args[1:]
    init_arg_defaults = init_args.defaults
    len_names = len(init_arg_names)
    len_defaults = len(init_arg_defaults)
    len_non_defaults = len_names - len_defaults
    args_dict = {}
    for i in range(len_names):
        name = init_arg_names[i]
        if name in kwargs.keys():
            value = kwargs[name]
        elif i >= len_non_defaults:
            j = i - len_non_defaults
            value = init_arg_defaults[j]
        else:
            raise Exception('Arguments of a configurable class without default value must be provided by a value in the decorator.')
        c = _get_config(value)
        args_dict[name] = value if c is None else c
    
    @classmethod
    def default_config(cls, **kwargs):
        cfg = Config(cls)
        cfg.setattrs(args_dict)
        cfg.setattrs(kwargs)
        cfg.freeze()
        return cfg
    
    def current_config(self):
        cfg = self.default_config()
        for k, v in cfg.__dict__.items():
            if k == 'cls' or k =='isfrozen':
                continue
            if hasattr(self, k):
                m = getattr(self, k)
                c = _get_config(m)
                c = c or m
                setattr(cfg, k, c)
        return cfg
    
    @classmethod
    def from_config(cls, cfg):
        assert cfg.cls is cls
        kwargs = cfg.__dict__.copy()
        kwargs.pop('isfrozen')
        cls = kwargs.pop('cls')
        for k, v in kwargs.items():
            if isinstance(v, Config):
                kwargs[k] = v.create_object()
        model = cls(**kwargs)
        return model
    
    cls.default_config = default_config
    cls.current_config = current_config
    cls.from_config = from_config
    
    return cls
    
        
