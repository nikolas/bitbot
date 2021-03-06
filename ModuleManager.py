import glob, imp, inspect, os, sys, uuid

BITBOT_HOOKS_MAGIC = "__bitbot_hooks"

class BaseModule(object):
    def __init__(self, bot, events, exports):
        pass

class ModuleManager(object):
    def __init__(self, bot, events, exports, directory="modules"):
        self.bot = bot
        self.events = events
        self.exports = exports
        self.directory = directory
        self.modules = {}
        self.waiting_requirement = {}
    def list_modules(self):
        return sorted(glob.glob(os.path.join(self.directory, "*.py")))

    def _module_name(self, path):
        return os.path.basename(path).rsplit(".py", 1)[0].lower()
    def _module_path(self, name):
        return os.path.join(self.directory, "%s.py" % name)

    def _load_module(self, name):
        path = self._module_path(name)

        with open(path) as module_file:
            while True:
                line = module_file.readline().strip()
                line_split = line.split(" ")
                if line and line.startswith("#--"):
                    # this is a hashflag
                    if line == "#--ignore":
                        # nope, ignore this module.
                        return None
                    elif line_split[0] == "#--require-config" and len(
                            line_split) > 1:
                        if not line_split[1].lower() in self.bot.config or not self.bot.config[
                                    line_split[1].lower()]:
                            # nope, required config option not present.
                            return None
                    elif line_split[0] == "#--require-module" and len(
                            line_split) > 1:
                        if not "bitbot_%s" % line_split[1].lower() in sys.modules:
                            if not line_split[1].lower() in self.waiting_requirement:
                                self.waiting_requirement[line_split[1].lower()] = set([])
                                self.waiting_requirement[line_split[1].lower()].add(path)
                            return None
                else:
                    break
        module = imp.load_source(name, path)

        if not hasattr(module, "Module"):
            raise ImportError("module '%s' doesn't have a Module class.")
        if not inspect.isclass(module.Module):
            raise ImportError("module '%s' has a Module attribute but it is not a class.")

        context = str(uuid.uuid4())
        context_events = self.events.new_context(context)
        context_exports = self.exports.new_context(context)
        module_object = module.Module(self.bot, context_events,
            context_exports)

        if not hasattr(module_object, "_name"):
            module_object._name = name.title()
        for attribute_name in dir(module_object):
            attribute = getattr(module_object, attribute_name)
            if inspect.ismethod(attribute) and hasattr(attribute,
                    BITBOT_HOOKS_MAGIC):
                hooks = getattr(attribute, BITBOT_HOOKS_MAGIC)
                for hook in hooks:
                    context_events.on(hook["event"]).hook(attribute,
                        **hook["kwargs"])

        module_object._context = context
        module_object._import_name = name

        assert not module_object._name in self.modules, (
            "module name '%s' attempted to be used twice.")
        return module_object

    def load_module(self, name):
        try:
            module = self._load_module(name)
        except ImportError as e:
            self.bot.log.error("failed to load module \"%s\": %s",
                [name, e.msg])
            return
        if module:
            self.modules[module._import_name] = module
            if name in self.waiting_requirement:
                for requirement_name in self.waiting_requirement:
                    self.load_module(requirement_name)
            self.bot.log.info("Module '%s' loaded", [name])
        else:
            self.bot.log.error("Module '%s' not loaded", [name])

    def load_modules(self, whitelist=[], blacklist=[]):
        for path in self.list_modules():
            name = self._module_name(path)
            if name in whitelist or (not whitelist and not name in blacklist):
                self.load_module(name)

    def unload_module(self, name):
        module = self.modules[name]
        del self.modules[name]

        context = module._context
        self.events.purge_context(context)
        self.exports.purge_context(context)

        del sys.modules[name]
        references = sys.getrefcount(module)
        del module
        references -= 1 # 'del module' removes one reference
        references -= 1 # one of the refs is from getrefcount

        self.bot.log.info("Module '%s' unloaded (%d reference%s)",
            [name, references, "" if references == 1 else "s"])
