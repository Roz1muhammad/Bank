def method(name=None):
    """
    Metodlar uchun dekorator.
    Masalan: @method(name="transfer.create")
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)
        wrapper.__name__ = name or func.__name__
        return wrapper
    return decorator
