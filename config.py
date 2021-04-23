import inspect
from functools import partial



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
    
    
    
    
    
    
def configurable(**kwargs):
    return partial(_configurable, **kwargs)
    
    
def _configurable(cls, **kwargs):
    init_args = inspect.getfullargspec(cls.__init__)
    init_arg_names = init_args.args[1:]
    init_arg_defaults = init_args.defaults
    len_names = len(init_arg_names)
    len_defaults = len(init_arg_defaults)
    args_dict = {}
    for i in range(len_names - len_defaults):
        name = init_arg_names[i]
        if not name in kwargs.keys():
            raise Exception('Arguments of a configurable class without default value must be provided by a value in the decorator.')
        value = kwargs[name]
        args_dict[name] = value
    for j in range(len_defaults):
        i = j + (len_names - len_defaults)
        name = init_arg_names[i]
        if name in kwargs.keys():
            value = kwargs[name]
        else:
            value = init_arg_defaults[j]            
        args_dict[name] = value
    for k, v in args_dict.items():
        if hasattr(v, 'current_config'):
            args_dict[k] = v.current_config()
    
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
                v = getattr(self, k)
            if hasattr(v, 'current_config'):
                v = v.current_config()
            setattr(cfg, k, v)
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
    
        
