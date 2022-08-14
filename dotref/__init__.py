#!/usr/bin/env python
import os
import sys
import pathlib
import argparse
import string
import json
import enum
import copy

__version__ = '1.2.2'


class ProfileError(Exception):
    """ Failed to parse a profile file """


class TemplateVarError(Exception):
    """ Undefined template variable """
    def __init__(self, name):
        super().__init__(f'Undefined variable {name}')
        self.name = name


class Logger:
    """ Simple console logger with ANSI color support """

    RESET   = '\033[0m'
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN    = '\033[96m'

    def __init__(self):
        self.colored = (sys.stdout.isatty() and
            os.environ.get('DOTREF_NO_COLOR') is None and
            os.environ.get('NO_COLOR') is None)

    def out(self, message, newline=False):
        sys.stdout.write(message + ('\n' if newline else ''))

    def err(self, message):
        sys.stderr.write(self.colorize(message, Logger.RED) + '\n')

    def hl(self, message):
        return self.colorize(message, Logger.YELLOW)

    def title(self, message):
        return self.colorize(message, Logger.MAGENTA)

    def muted(self, message):
        return self.colorize(message, Logger.BLUE)

    def colorize(self, message, color):
        return ('{}{}{}'.format(self.color(color), message, self.color(Logger.RESET)))

    def color(self, color):
        return color if self.colored else ''

    def print_tree(self, root, get_name, get_children, child_prefix='+-- '):
        self.out(get_name(root), True)
        self.__print_tree(root, get_name, get_children, '', child_prefix)

    def __print_tree(self, node, get_name, get_children, prefix, child_prefix):
        child_count = len(get_children(node))
        for i, child in enumerate(get_children(node)):
            self.out(prefix + child_prefix + get_name(child), True)
            p = prefix + ('|' if i < child_count - 1 else ' ').ljust(len(child_prefix))
            self.__print_tree(child, get_name, get_children, p, child_prefix)


class ActionType(enum.Enum):
    """ Type of the action (or command) to execute """

    STATUS = 0
    SYNC   = 1
    UNLINK = 2


class ActionState(enum.Enum):
    """ Directory/link/template states """

    OK       = (0, Logger.GREEN)
    MISSING  = (1, Logger.YELLOW)
    CONFLICT = (2, Logger.RED)
    CREATED  = (3, Logger.GREEN)
    LINKED   = (4, Logger.GREEN)
    UNLINKED = (5, Logger.GREEN)
    DIFFERS  = (6, Logger.YELLOW)
    RENDERED = (7, Logger.GREEN)

    def str(self, log):
        return log.colorize(('[' + self.name + ']').ljust(10), self.value[1])


class StateFile:
    """ Sate file that keeps dotref state and config for a given repository """

    def __init__(self, filename):
        self.filename = filename

        json_state = None
        if filename.is_file():
            with open(filename, 'r') as f:
                json_state = json.load(f)

        self.profile = None

        if json_state and 'profile' in json_state:
            if not isinstance(json_state['profile'], str):
                raise TypeError('Name of the current profile in the state file must be a string')
            self.profile = json_state['profile']

    def save(self):
        with open(self.filename, 'w') as f:
            f.write(json.dumps(self.to_json()))

    def to_json(self):
        return {'profile': self.profile} if self.profile else {}


class ProfileEntry:
    """ Generic profile entry: a variable or action """

    def __init__(self, profile_name):
        self.profile = profile_name


class Variable(ProfileEntry):
    """ "vars" entry """

    def __init__(self, profile_name, name, value):
        super().__init__(profile_name)
        self.name = name
        self.value = value


class CreateAction(ProfileEntry):
    """ "create" directory """

    def __init__(self, profile_name, json_action):
        super().__init__(profile_name)
        self.mode = None

        if not isinstance(json_action, dict):
            raise TypeError('"create" element must be an object')

        if 'name' not in json_action or not isinstance(json_action['name'], str):
            raise TypeError('"create" must have "name" field of type string')

        if 'mode' in json_action:
            if not isinstance(json_action['mode'], str):
                raise TypeError('"create.mode" field must be a string containing octal integer')
            self.mode = int(json_action['mode'], 8)

        self.name = json_action['name']

    def apply(self, command):
        state = None
        orig_path = pathlib.Path(self.name)
        target = orig_path.expanduser()

        if target.exists():
            if target.is_dir():
                state = ActionState.OK
            else:
                state = ActionState.CONFLICT
        else:
            if command == ActionType.STATUS:
                state = ActionState.MISSING
            elif command == ActionType.SYNC:
                if self.mode:
                    target.mkdir(parents=True, exist_ok=True, mode=self.mode)
                else:
                    target.mkdir(parents=True, exist_ok=True)
                state = ActionState.CREATED
            else:
                state = ActionState.OK

        return (state, orig_path, None)


class SrcDstAction(ProfileEntry):
    """ abstract action that has src and dst fields """

    def __init__(self, type, profile_name, json_action):
        super().__init__(profile_name)

        if not isinstance(json_action, dict):
            raise TypeError(f'"{type}" element must be an object')

        if 'src' not in json_action or not isinstance(json_action['src'], str):
            raise TypeError(f'"{type}" must have "src" field of type string')

        if 'dst' not in json_action or not isinstance(json_action['dst'], str):
            raise TypeError(f'"{type}" must have "dst" field of type string')

        self.src = json_action['src']
        self.dst = json_action['dst']

    def __eq__(self, other):
        return (self.src, self.dst) == (other.src, other.dst)


class LinkAction(SrcDstAction):
    """ "link" file/directory """

    def __init__(self, profile_name, json_action):
        super().__init__('link', profile_name, json_action)

    def apply(self, command):
        state = None
        orig_src = pathlib.Path(self.src)
        src = orig_src.resolve()
        orig_dst = pathlib.Path(self.dst)
        dst = orig_dst.expanduser()

        if not src.exists():
            raise ValueError(f'The source file or directory to link "{self.src}" does not exist')

        if dst.exists():
            if dst.samefile(src):
                if command == ActionType.UNLINK:
                    dst.unlink()
                    state = ActionState.UNLINKED
                else:
                    state = ActionState.OK
            else:
                state = ActionState.CONFLICT
        else:
            if command == ActionType.SYNC:
                dst.symlink_to(src, src.is_dir())
                state = ActionState.LINKED
            elif command == ActionType.UNLINK:
                state = ActionState.OK
            else:
                state = ActionState.MISSING
        return (state, orig_src, orig_dst)


class TemplateAction(SrcDstAction):
    """ "template" entry """

    def __init__(self, profile_name, json_action):
        super().__init__('template', profile_name, json_action)

    def apply(self, command, vars):
        src = pathlib.Path(self.src)
        orig_dst = pathlib.Path(self.dst)
        dst = orig_dst.expanduser()
        dst_exists = dst.exists()

        if dst_exists:
            if not dst.is_file():
                return (ActionState.CONFLICT, src, orig_dst)
        elif command != ActionType.SYNC:
            return (ActionState.OK if command == ActionType.UNLINK else ActionState.MISSING, src, orig_dst)

        with open(src, 'r') as src_file:
            tpl = string.Template(src_file.read())

            try:
                rendered = tpl.substitute(vars)
            except KeyError as e:
                raise TemplateVarError(str(e))

            with open(dst, 'r+' if dst_exists else 'w') as dst_file:
                if dst_exists:
                    dst_content = dst_file.read()
                    if rendered == dst_content:
                        if command == ActionType.UNLINK:
                            dst.unlink()
                            return (ActionState.UNLINKED, src, orig_dst)
                        else:
                            return (ActionState.OK, src, orig_dst)
                    elif command != ActionType.SYNC:
                        return (ActionState.DIFFERS, src, orig_dst)

                    dst_file.seek(0)

                dst_file.write(rendered)

                if dst_exists:
                    dst_file.truncate()

                return (ActionState.RENDERED, src, orig_dst)


class Profile:
    """ Configuration profile: a collection of variables and actions """

    def __init__(self, filename):
        self.name = filename.with_suffix('').name
        self.parents = []

        try:
            with open(filename, 'r') as f:
                json_profile = json.load(f)

                self.extends = Profile.__parse_extends(json_profile)
                self.vars = self.__parse_vars(json_profile)
                self.create = self.__parse_create(json_profile)
                self.link = self.__parse_link(json_profile)
                self.template = self.__parse_template(json_profile)
        except Exception as e:
            raise ProfileError(f'Failed to load profile "{self.name}": {str(e)}') from e

    def merged(self):
        result = copy.deepcopy(self)

        for parent in self.parents:
            pm = parent.merged()
            result.vars.extend([v for v in pm.vars if not any(rv.name == v.name for rv in result.vars)])
            result.create.extend([c for c in pm.create
                if not any(rc.name == c.name for rc in result.create)])
            result.link.extend([link for link in pm.link if link not in result.link])
            result.template.extend([t for t in pm.template if t not in result.template])

        return result

    def pretty_print(self, log):
        log.print_tree(self, lambda p: log.hl(p.name) if p.name == self.name else log.muted(p.name),
                lambda p: p.parents)

        merged = self.merged()
        merged.__pretty_print_entries(log, merged.vars, 'Variables', lambda v: v.name, lambda v: v.value)
        merged.__pretty_print_entries(log, merged.create, 'Create', lambda c: c.name,
                lambda c: oct(c.mode) if c.mode else 'default mode')
        merged.__pretty_print_entries(log, merged.link, 'Link', lambda l: l.src, lambda l: l.dst)
        merged.__pretty_print_entries(log, merged.template, 'Template', lambda t: t.src, lambda t: t.dst)

    def action(self, command, log):
        log.out(f'Profile: {log.hl(self.name)}', True)
        has_conflicts = False
        merged = self.merged()

        if merged.create and command != ActionType.UNLINK:
            results = [a.apply(command) for a in merged.create]
            has_conflicts = any(r[0] == ActionState.CONFLICT for r in results)
            Profile.__print_action_results(log, 'Create', results)

        if merged.link:
            results = [a.apply(command) for a in merged.link]
            has_conflicts = has_conflicts or any(r[0] == ActionState.CONFLICT for r in results)
            Profile.__print_action_results(log, 'Link', results)

        if merged.template:
            vars = {v.name: v.value for v in merged.vars}
            results = [a.apply(command, vars) for a in merged.template]
            has_conflicts = has_conflicts or any(r[0] == ActionState.CONFLICT for r in results)
            Profile.__print_action_results(log, 'Template', results)

        log.out(f'\n{log.hl(command.name.lower())} completed successfully ' +
            ('but conflicts were detected' if has_conflicts else 'and no conflicts were detected'), True)

    def __pretty_print_entries(self, log, entries, header, get_name, get_val):
        if entries:
            name_width = max([len(get_name(var)) for var in entries]) + 1
            log.out(log.title(f'\n{header}:'), True)
            for e in entries:
                log.out(f'    {log.hl((get_name(e) + ":").ljust(name_width))} {get_val(e)}')
                log.out(log.muted(f' ({e.profile})') if e.profile != self.name else '', True)

    @staticmethod
    def __print_action_results(log, header, results):
        log.out(log.title(f'\n{header}:'), True)
        left_width = max([len(str(r[1])) for r in results]) + 1

        for state, left, right in results:
            log.out('    ' + state.str(log) + ' ' + Profile.__print_path(log, left, left_width))
            if right:
                log.out(' ->  ' + Profile.__print_path(log, right, None))
            log.out('', True)

    @staticmethod
    def __print_path(log, path, width):
        plain_len = len(str(path.parent) + os.sep + path.name)
        highlighted = str(path.parent) + os.sep + log.hl(path.name)
        return highlighted + (' ' * (width + 2 - plain_len) if width else '')

    @staticmethod
    def __parse_extends(json_profile):
        result = []
        extends = json_profile.get('extends')
        if extends:
            if not isinstance(extends, list):
                raise TypeError('"extends" field must be a list of strings')
            for name in extends:
                if not isinstance(name, str):
                    raise TypeError('"extends" profile name must be a string')
                result.append(name)
        return result

    def __parse_vars(self, json_profile):
        result = []
        variables = json_profile.get('vars')
        if variables:
            if not isinstance(variables, dict):
                raise TypeError('"vars" field must be an object')

            for name, value in variables.items():
                if not isinstance(name, str) or not isinstance(value, str):
                    raise TypeError('Variable name and value must be strings')
                result.append(Variable(self.name, name, value))
        return result

    def __parse_create(self, json_profile):
        create = json_profile.get('create')
        if create:
            if not isinstance(create, list):
                raise TypeError('"create" must be a list of objects')
            return [CreateAction(self.name, action) for action in create]
        return []

    def __parse_link(self, json_profile):
        links = json_profile.get('link')
        if links:
            if not isinstance(links, list):
                raise TypeError('"link" must be a list of objects')
            return [LinkAction(self.name, link) for link in links]
        return []

    def __parse_template(self, json_profile):
        templates = json_profile.get('template')
        if templates:
            if not isinstance(templates, list):
                raise TypeError('"templates" must be a list of objects')
            return [TemplateAction(self.name, template) for template in templates]
        return []


class Dotref:
    """ Main Dotref application """

    def __init__(self, log, args):
        self.log = log
        self.dotdir = pathlib.Path(args.dotdir)
        self.profile = args.profile

        self.statefile = StateFile(self.dotdir / args.statefile)
        self.profs = self.__load_profiles()

    def do(self, command):
        getattr(self, command)()

    def init(self):
        if not self.profile:
            raise ValueError('Please provide a profile name using "--profile" argument')

        if self.profile not in self.profs:
            raise ValueError(f'Profile "{self.profile}" not found')

        self.statefile.profile = self.profile
        self.statefile.save()
        self.log.out(f'Successfully initialized to use profile {self.log.hl(self.profile)}', True)

    def sync(self):
        self.__execute_command(ActionType.SYNC)

    def unlink(self):
        self.__execute_command(ActionType.UNLINK)

    def status(self):
        self.__execute_command(ActionType.STATUS)

    def profiles(self):
        if self.profile:
            self.__show_single_profile()
        else:
            self.__show_all_profiles()

    def __load_profiles(self):
        filenames = [f for f in self.dotdir.glob('*.json') if f.is_file() and
                self.statefile.filename.name != f.name and not f.name.startswith('.')]

        profiles = {p.name: p for p in map(Profile, filenames)}

        for name, profile in profiles.items():
            parents = []
            for parent in profile.extends:
                if parent not in profiles:
                    raise ProfileError(f'Profile "{name}" extends "{parent}" but it does not exist')
                parents.append(profiles[parent])
            profile.parents = parents

        return profiles

    def __show_all_profiles(self):
        if not self.profs:
            self.log.out(f'No profile files found in {self.log.hl(self.dotdir)} directory', True)
        else:
            names = sorted([n for n in self.profs.keys()
                if not self.statefile.profile or self.statefile.profile != n])
            if self.statefile.profile and self.statefile.profile in self.profs:
                names.insert(0, self.statefile.profile)

            name_width = max(len(name) for name in names) + 1

            for name in names:
                p = self.profs[name]
                wide_name = name.ljust(name_width)
                pretty_name = self.log.hl(wide_name) if self.statefile.profile == name else wide_name
                extends = self.log.muted('(' + (', '.join(p.extends) + ')')) if p.extends else ''
                self.log.out(f'{pretty_name}{extends}', True)

            if self.statefile.profile:
                self.log.out(f'\nCurrent profile: {self.log.hl(self.statefile.profile)}', True)
            else:
                self.log.out(f'\nCurrent profile is not set, '
                    f'use "{self.log.hl("dotref init -p PROFILE")}" to set current profile', True)

    def __show_single_profile(self):
        p = self.profs.get(self.profile)
        if not p:
            raise ValueError(f'Profile "{self.profile}" not found')
        p.pretty_print(self.log)

    def __execute_command(self, command):
        if not self.statefile.profile:
            raise ValueError('Please run "dotref init" first to select a profile')

        if self.statefile.profile not in self.profs:
            raise ValueError(f'Profile "{self.statefile.profile}" not found')

        self.profs[self.statefile.profile].action(command, self.log)


def main():
    log = Logger()

    parser = argparse.ArgumentParser(description='Simple tool to manage dotfiles')
    parser.add_argument('command', choices=['init', 'sync', 'unlink', 'status', 'profiles', 'version'],
        help='Command to execute')
    parser.add_argument('-p', '--profile',
        help=f'Name of the profile to use for {log.hl("init")} and {log.hl("profiles")} commands. \
                Use {log.hl("profiles")} to see all available profiles.')
    parser.add_argument('-d', '--dotdir', default='dotref',
        help=f'Directory containing dotref profiles and state file (default: {log.muted("dotref")})')
    parser.add_argument('-s', '--statefile', default='.dotref.json',
        help=f'Name of the state file in which dotref will keep current profile and settings \
                (default: {log.muted(".dotref.json")} in the DOTDIR directory)')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='Produce more verbose output')
    args = parser.parse_args()

    if args.command == 'version':
        log.out(f'dotref {log.hl(__version__)}', True)
    else:
        try:
            dotref = Dotref(log, args)
            dotref.do(args.command)
        except Exception as e:
            log.err(f'\nError: {str(e)}')
            if args.verbose > 0:
                raise
            else:
                sys.exit(1)


if __name__ == '__main__':
    main()
