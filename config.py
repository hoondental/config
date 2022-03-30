import inspect
from functools import partial
import copy

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
            else:
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
        self.configs = copy.deepcopy(configs)
        self.freeze()
        
       
    def __str__(self, prefix=''):
        result = prefix + 'cls : ' + str(self.cls) + '\n'
        for i, c in enumerate(self.configs):
            result += prefix + str(i) + ' : ' + '\n' + c.__str__(prefix=prefix+'    ')
        return result
    
    def __repr__(self, prefix=''):
        result = prefix + 'cls : ' + str(self.cls) + '\n'
        for i, c in enumerate(self.configs):
            result += prefix + str(i) + ' : ' + '\n' + c.__repr__(prefix=prefix+'    ')
        return result
    
    def __getitem__(self, i):
        return self.configs[i]
    
    def __len__(self):
        return len(self.configs)
    
    def append(self, c):
        assert isinstance(c, Config)
        self.configs.append(c)
        
    def insert(self, idx, c):
        assert isinstance(c, Config)
        self.configs.insert(idx, c)
        
    def remove(self, x):
        self.configs.remove(x)
        
    def pop(self, idx):
        return self.configs.pop(idx)        
        
    def create_object(self):
        _torch = True
        models = []
        for c in self.configs:
            m = c.create_object()
            if not isinstance(m, nn.Module):
                _torch = False
            models.append(m)
        if _torch and len(self.configs) > 0:
            models = nn.ModuleList(models)
        return models
        
        
class ConfigDict(Config):
    def __init__(self, configs={}):
        self.cls = type(self)
        for k, v in configs.items():
            assert isinstance(v, Config)
        self.configs = copy.deepcopy(configs)
        self.freeze()
        
    def create_object(self):
        _torch = True
        models = {}
        for k, v in self.configs.items():
            m = v.create_object()
            if not isinstance(m, nn.Module):
                _torch = False
            models[k] = m
        if _torch and len(self.configs) > 0:
            models = nn.ModuleDict(models)
        return models
    
    def __str__(self, prefix=''):
        result = prefix + 'cls : ' + str(self.cls) + '\n'
        for k, v in self.configs.items():
            result += prefix + k + ' : ' + '\n' + v.__str__(prefix=prefix+'    ')
        return result
    
    def __repr__(self, prefix=''):
        result = prefix + 'cls : ' + str(self.cls) + '\n'
        for k, v in self.configs.items():
            result += prefix + k + ' : ' + '\n' + v.__repr__(prefix=prefix+'    ')
        return result
    
    def __getitem__(self, i):
        return self.configs[i]
    
    def __setitem__(self, i, v):
        assert isinstance(v, Config)
        self.configs[i] = v
        
    def __len__(self):
        return len(self.configs)
        
    def keys(self):
        return self.configs.keys()
    
    def values(self):
        return self.configs.values()
    
    def items(self):
        return self.configs.items()
    
    
def get_config(m):
    if hasattr(m, 'current_config'):
        return m.current_config()
    elif isinstance(m, list) or isinstance(m, tuple) or isinstance(m, nn.ModuleList):
        cfgs = []
        for _m in m:
            _c = get_config(_m)
            if _c is None:
                return None
            cfgs.append(_c)
        return ConfigList(cfgs)
    elif isinstance(m, dict) or isinstance(m, nn.ModuleDict):
        cfgs = {}
        for _k, _m in m.items():
            _c = get_config(_m)
            if _c is None:
                return None
            cfgs[_k] = _c
        return ConfigDict(cfgs)
    else:
        return None      
    
    
def configurable(**kwargs):
    return partial(_configurable, **kwargs)
    
    
def _configurable(cls, **kwargs):
    init_args = inspect.getfullargspec(cls.__init__) # self 와 디폴트 인자 포함, *args 와 **kwargs 제외
    init_arg_names = init_args.args[1:]  # self 제외한 argument 이름의 리스트
    init_arg_defaults = init_args.defaults or [] # 디폴트 인자의 값
    len_names = len(init_arg_names)
    len_defaults = len(init_arg_defaults)
    len_non_defaults = len_names - len_defaults
    cfgs_dict = {} #  init_args 에 대한 {변수명:Config 또는 None}
    args_dict = {} # init_args 에 대한 {변수명:초기값}
    cfgargs_dict = {} # init_args 에 대한 {변수명:Config 또는 초기값}
    for i, name in enumerate(init_arg_names): # range(len_names):
#        name = init_arg_names[i]
        if name in kwargs.keys():
            value = kwargs[name]
        elif i >= len_non_defaults:
            j = i - len_non_defaults
            value = init_arg_defaults[j]
        else:
            raise Exception('Arguments of a configurable class without default value must be provided by a value in the decorator.')
        c = get_config(value)
        cfgs_dict[name] = c
        args_dict[name] = value
        cfgargs_dict[name] = value if c is None else c
        
    cls.old__init__ = cls.__init__          
    def new__init__(self, *args, **kwargs):
        _args = []
        _kwargs = {}
        for i, v in enumerate(args):
            k = init_arg_names[i]
            _kwargs[k] = v
        for k, v in kwargs.items():
            _kwargs[k] = v
        for k in init_arg_names:
            if k in _kwargs.keys():
                continue
            v = args_dict[k]
            _kwargs[k] = v
#            _kwargs[k] = arg.current_config().create_object() if hasattr(arg, 'current_config') else arg # init 함수 인자로 Config 객체를 넣지 않음
        cls.old__init__(self, **_kwargs)        
        for k, v in _kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)    # __init__ 초기화 함수의 인자는 자동으로 self 의 어트리뷰트로 등록되어 있지 않으면 자동으로 등록함.
    cls.__init__ = new__init__        
     
    @classmethod
    def default_config(cls, **kwargs):
        cfg = Config(cls)
        cfg.setattrs(copy.deepcopy(cfgargs_dict))
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
                c = get_config(m)
                c = m if c is None else c
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

    
        
