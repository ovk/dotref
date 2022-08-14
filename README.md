# dotref

[![Tests](https://github.com/ovk/dotref/actions/workflows/tests.yml/badge.svg)](https://github.com/ovk/dotref/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/ovk/dotref/badge.svg?branch=master)](https://coveralls.io/github/ovk/dotref?branch=master)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/ovk/dotref.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/ovk/dotref/context:python)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dotref)](https://pypi.python.org/pypi/dotref)


`dotref` is a simple tool to manage dotfiles across multiple devices.
It supports creating directories, symlinks, templating and hierarchical configuration profiles to keep things DRY.

---

<p align="center">
  <img width="600" src="./demo.svg">
</p>

# Feature Highlight
- Create symlinks to dotfiles and directories
- Create directories
- Configuration files templating
- Hierarchical configuration profiles to easily manage dotfiles across multiple devices

## Why another dotfile manager?
While there are many dotfile managers available, most of them are either too complex (try to do everything, often in opinionated ways)
or way to limited.
Dotref is an attempt to make simple but useful tool, that focuses just on dotfile management ("do one thing and do it well").

Some highlight of what makes dotref different from some other tools:

- Dotfiles are managed according to hierarchical profiles (that are just simple JSON files).
That was the main reason for the creation of dotref, as at least at the moment it was originally created, no other tool could do that.
This makes it very easy to manage configuration for multiple devices (e.g. servers, desktops, virtual machines) while following DRY principle.
- Dotref is a single Python script without any dependencies on third-party tools or libraries.
The whole script is just a few hundred lines long and can be easily reviewed and audited by anyone with basic Python knowledge.
- Dotref doesn't make any assumptions about where dotfiles will be stored.
For example, while many people keep them in a Git repository, they may as well be stored on Dropbox or Nextcloud.

# Overview
Dotref works mostly by just creating symlinks to your dotfiles.
How does it know what to link where? This is described in dotref profile files.

## Profiles
A profile file is a simple JSON file that describes what you want dotref to do with your dotfiles.

By default, all profiles are stored in a `dotref` directory, inside the directory containing your dotfiles.
It's often useful to keep dotfiles in a Git (or other VCS) repository and the dotref profiles should be kept there as well.

Profile files can be created manually in your favorite text editor and they have the following structure:

```json
{
  "extends": "... List of parent profile names ..."
  "vars":    "... Object with variables for templating ...",
  "create":  "... List of directories to create ...",
  "link":    "... List of symlinks to create ...",
  "template":"... List of templates to render ..."
}
```

Profile name is simply its filename without the `.json` extension.

Let's take a look at profile structure:

- `extends` is a list of parent profile names.
If a profile *Child* extends profile *Root* then everything from the *Root* profile will also be available in the *Child* profile.
If there's an overlap (for example, a child defines a variable with the same name), the *Child* properties will override its parent's properties.
`extends` field can be omitted for a root profiles.
- `vars` is a JSON object with variables for template substitution. An example: `"vars": { "email": "john.doe@example.com" }`.
- `create` is a list of JSON objects describing what directories need to be created.
Each object must have a `name` field with the directory name and can optionally have `mode` with a string containing octal directory permissions.
An example: `"create": [ { "name": "~/games", "mode": "750" } ]`.
Note that `mode` is always affected by `umask` and if not specified the default value is `777`.
- `link` is a list of JSON objects describing symlinks that need to be created.
Each object must have `src` and `dst` fields representing link source and destination.
An example: `"link": [ { "src": "bashrc", "dst": "~/.bashrc" } ]` will create a `~/.bashrc` symlink pointing to the `bashrc` file in the current directory.
- `template` is a list of JSON objects describing what templates to render.
Each object must have `src` and `dst` fields representing template source file and its rendered file destination.
An example: `"template": [ { "src": "bashrc.tpl", "dst": "~/.bashrc" } ]` will create a `~/.bashrc` file by rendering a template file `bashrc.tpl`.

### Profile hierarchy
Having profile inheritance allows to avoid copy-pasting the same configuration when managing multiple devices.
It can be best explained on example: one can imagine a `base` profile which symlinks configuration for some common tools, shell, text editor, etc.
We can create two other profiles that extend `base`: a `server` profile with extra configurations that only relevant on a server,
and a `desktop` one for desktops.
As a parallel hierarchy, we could create two profiles: `home` and `work`, each defining variables relevant to corresponding environment.
Then the final profiles like `home_server`, `work_laptop` or `home_laptop` could just extend corresponding profiles.
The whole hierarchy in this case can be visualized as follows:

```
home_server        home_laptop    work_laptop
    |                  |              |
    |\                / \            /|
    | \              /   \          / |
    |  \            /     \        /  |
    |   \          /       \      /   |
 server  \- home -/         desktop   work
    \                         /
     \                       /
      \------- base --------/
```

## Templating
Templating in dotref is simply a variable substitution in any text file.
A template file is "rendered" when all of its variable placeholders (denoted with leading `$` sign) replaced with actual variable values from the desired profile.

Templating is based on Python's built-in [templates](https://docs.python.org/3/library/string.html#template-strings).

Here's an example of templating Git configuration file:

```
[user]
    name = $git_name
    email = $email
    signingKey = $git_key
```

Here `git_name`, `email` and `git_key` are variables that must be defined in a profile.

If a template uses undefined variable, it will throw an error when this template is used.

> **Note**
> Templating can also be used to just copy a file to a destination. If a file doesn't have any variables, it will be copied as-is.
> This can be convenient for cases when symbolic links are undesirable.

## Commands
Dotref must be invoked with a specific command, which is one of: `version`, `profiles`, `init`, `status`, `sync`, `unlink`.
The only exception is when called with `-h` flag, which prints help and doesn't require a command.

### Version
The `version` command just prints current dotref version.

### Profiles
The `profiles` command prints a list of all profiles in a given repository.
By default, profile files are searched in the `dotref` subdirectory in a current directory, but this can be specified using the `d DOTDIR, --dotdir DOTDIR` argument.

The `profiles` command can also show detailed information about a single profile, when invoked with `-p PROFILE, --profile PROFILE` argument.
It will show ancestors tree of the profile and detailed info about which parts of the configuration were taken from which profile.

### Init
The `init` command selects and remembers what profile should be used on a given system.
Thus it must always be invoked with the `-p PROFILE, --profile PROFILE` argument.

The selected profile is stored in a file called dotref statefile, under the `dotref` directory.
This file is named `.dotref.json` by default, but this can be overridden using the `-s STATEFILE, --statefile STATEFILE` argument.

The `init` command can be used to change the current profile but this should be done with caution,
as applying one profile on top of another can lead to unexpected results.
It's best to first do `dotref unlink` before running `dotref init` again.

### Status
The `status` command checks if the system configuration matches the current profile.
It's somewhat similar to `git status` and for every entry of a profile (including all it's ancestors) it will show the status of the entry.

More about statuses below.

### Sync
The `sync` command tries to bring the system in the desired state described by the current profile.
This command is idempotent, so it can be safely executed multiple times and if the system is already in the desired state it will only print status without doing anything.

A profile entry (directory, symlink or template) can be in one of the following states:

- `OK`: entry already in the desired state, no changes were made
- `MISSING`: entry doesn't exist in its destination
- `CREATED`: directory was created successfully
- `LINKED`: symlink was created successfully
- `UNLINKED`: symlink was removed successfully
- `RENDERED`: template was rendered to its destination successfully
- `DIFFERS`: rendered template version differs from the actual template
- `CONFLICT`: a conflicting object (file/directory/symlink) already exists at the destination

It's important to mention that all conflicts must be resolved manually.
For example, if dotref is told to link `~/.bashrc` but it already exists and it's not a symlink to the desired file - this will cause a conflict,
and it's up to the user to decide what to do with the existing file.

The `sync` operation processes profile entries in the following order:

- First all directories are created
- Links are created after the directories, since a link destination could be inside a created directory
- Templates are rendered after the links and directories are created, since template destination could be in any of them

### Unlink
The `unlink` command is the opposite of `sync` - it tries to safely remove everything that's described in the current profile and its ancestors.
The `unlink` operation is very conservative and it won't remove created directories or rendered templates (unless they exactly match to the actual template).

# Quick Start
Let's assume you have a `dotfiles` directory with the following files in it:

```
$ ls
bashrc  gitconfig.tpl  i3config
```

The `bashrc` and `i3config` represent your config files for Bash and i3 respectively.
The `gitconfig.tpl` file is a dotref template for the main Git config file:

```
$ cat gitconfig.tpl
[user]
    name = $git_name
    email = $email
```

As you can see, it uses two variables: `git_name` and `email`.

## Creating profiles
The first step is to create a dotref profiles directory and a root profile:

```
mkdir dotref
```

Let's create `dotref/base.json` file with the following content:

```json
{
  "vars": {
    "git_name": "jdoe",
    "email": "john.doe@example.com"
  },
  "create": [
    { "name": "~/.config/git" }
  ],
  "link": [
    { "src": "bashrc", "dst": "~/.bashrc" }
  ],
  "template": [
    { "src": "gitconfig.tpl", "dst": "~/.config/git/config" }
  ]
}
```

Here the `vars` block just defines values for our template variables.
The `create` block is to create a `~/.config/git` directory, if it doesn't already exist.
The `link` tells dotref we want to create a symlink `~/.bashrc` that will point at our `bashrc` file.
And finally the `template` block instructs dotref to render a template file `gitconfig.tpl` at the `~/.config/git/config` destination.

Now let's create a `dotref/desktop.json` file with the following content:

```json
{
  "extends": [ "base" ],
  "link": [
    { "src": "i3config", "dst": "~/.config/i3" }
  ]
}
```

The `"extends": [ "base" ]` line tells that this profile *extends* `base` profile,
so everything specified in the `base` profile will be also available in the `desktop` profile.
And the `link` block just tells that we want a `~/.config/i3` symlink to point to the `i3config` file.

We can see the merged view (view that combines profile entries from all of its ancestors)
of the `desktop` profile with the `dotref profiles` command:

```
$ dotref profiles -p desktop
desktop
+-- base

Variables:
    git_name: jdoe (base)
    email:    john.doe@example.com (base)

Create:
    ~/.config/git: default mode (base)

Link:
    i3config: ~/.config/i3
    bashrc:   ~/.bashrc (base)

Template:
    gitconfig.tpl: ~/.config/git/config (base)
```

## Selecting profile
Before applying a profile we need to select what profile we want to use on the system.
This is done with `dotref init` command:

```
> dotref init -p desktop
Successfully initialized to use profile desktop
```

Dotref remembers the current profile by storing it in the `dotref/.dotref.json` file, so we don't need to specify it again with every command.

## Applying profile
Before applying our profile let's check the current status of the system with the `dotref status` command:

```
$ dotref status
Profile: desktop

Create:
    [MISSING]  ~/.config/git

Link:
    [MISSING]  ./i3config  ->  ~/.config/i3
    [MISSING]  ./bashrc    ->  ~/.bashrc

Template:
    [MISSING]  ./gitconfig.tpl  ->  ~/.config/git/config
```

This output tells us that `~/.config/git` directory is missing, as well as the config files for Bash and i3,
and the git config template is missing as well.

To apply the profile run `dotref sync`:

```
$ dotref sync
Profile: desktop

Create:
    [CREATED]  ~/.config/git

Link:
    [LINKED]   ./i3config  ->  ~/.config/i3
    [LINKED]   ./bashrc    ->  ~/.bashrc

Template:
    [RENDERED] ./gitconfig.tpl  ->  ~/.config/git/config

sync completed successfully and no conflicts were detected
```

Here the dotref tells us that it did everything we asked it to do.
Let's try and read git config:

```
$ cat ~/.config/git/config
[user]
    name = jdoe
    email = john.doe@example.com
```

We can run `dotref sync` again:

```
$ dotref sync
Profile: desktop

Create:
    [OK]       ~/.config/git

Link:
    [OK]       ./i3config  ->  ~/.config/i3
    [OK]       ./bashrc    ->  ~/.bashrc

Template:
    [OK]       ./gitconfig.tpl  ->  ~/.config/git/config

sync completed successfully and no conflicts were detected
```

The `OK` states tell us that the dotref didn't do anything since the system is already in the desired state.
Let's now edit the `gitconfig.tpl` file to make it looks like this:

```
[user]
    name = $git_name
    email = $email

[core]
    editor = nvim
```

and run `dotref sync` again:

```
$ dotref sync
Profile: desktop

Create:
    [OK]       ~/.config/git

Link:
    [OK]       ./i3config  ->  ~/.config/i3
    [OK]       ./bashrc    ->  ~/.bashrc

Template:
    [RENDERED] ./gitconfig.tpl  ->  ~/.config/git/config

sync completed successfully and no conflicts were detected
```

Dotref realized that the Git config template was changed and re-rendered it.

## Unlinking profile
To remove symlinks and rendered templates that dotref have created run `dotref unlink` command:

```
$ dotref unlink
Profile: desktop

Link:
    [UNLINKED] ./i3config  ->  ~/.config/i3
    [UNLINKED] ./bashrc    ->  ~/.bashrc

Template:
    [UNLINKED] ./gitconfig.tpl  ->  ~/.config/git/config

unlink completed successfully and no conflicts were detected
```

Similarly to `sync`, the `unlink` command is idempotent and can be safely executed multiple times.

## Example
For a real-world example see [ovk/dotfiles](https://github.com/ovk/dotfiles) repository.

# CLI Usage
```
usage: dotref [-h] [-p PROFILE] [-d DOTDIR] [-s STATEFILE] [-v] {init,sync,unlink,status,profiles,version}

Simple tool to manage dotfiles

positional arguments:
  {init,sync,unlink,status,profiles,version}
                        Command to execute

options:
  -h, --help            show this help message and exit
  -p PROFILE, --profile PROFILE
                        Name of the profile to use for init and profiles commands. Use profiles to see
                        all available profiles.
  -d DOTDIR, --dotdir DOTDIR
                        Directory containing dotref profiles and state file (default: dotref)
  -s STATEFILE, --statefile STATEFILE
                        Name of the state file in which dotref will keep current profile and settings (default:
                        .dotref.json in the DOTDIR directory)
  -v, --verbose         Produce more verbose output
```

# Terminal Colors
By default dotref will use ANSI colors if possible.
This can be disabled be setting either `NO_COLOR` or `DOTREF_NO_COLOR` environment variables
(as per [no-color](https://no-color.org/) convention).

# Installation
Dotref's only dependency is Python 3.6 or newer.

## Manual installation
Dotref is just a single Python file with no dependencies, and can be easily installed manually:

```
curl https://raw.githubusercontent.com/ovk/dotref/master/dotref -o dotref
chmod +x dotref
sudo mv dotref /usr/local/bin
```

## PyPi
Dotref is also available as PyPi package [dotref](https://pypi.org/project/dotref/).

It can be installed with Pip:

```
sudo pip install dotref
```

## Arch Linux AUR Package
For Arch Linux, dotref can be installed from the AUR [dotref](https://aur.archlinux.org/packages/dotref/) package.

## Windows
Dotref works on Windows and has been tested in WSL2, MSYS2 and Cygwin (it may work in other environments as well).
It can be either installed manually or with `pip`.

## Shell Completion
Arch package includes shell auto-completion for Bash and Fish shells, which will be installed automatically.
For other types of installations, the completion [files](https://github.com/ovk/dotref/tree/master/completions)
can be downloaded and installed manually, if desired.

