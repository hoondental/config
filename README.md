# config
config class and decorator


# Pattern
from config import Config, configurable

class B:
    pass

@configurable()
class A:
    def __init__(self, a=2, b=B()):
        self.a = a
        self.b = b      
        
        
# Effects
Generate 3 functions.(default_config, current_config, from_config)

![image](https://user-images.githubusercontent.com/16496732/115883411-b5f26000-a488-11eb-8c59-0288ac67ba9c.png)
