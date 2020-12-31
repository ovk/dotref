`dotref` is a simple tool for dotfile management.
It is implemented as a single Python script with no dependencies on any third-party libraries.

# Installation
Python 3.6+ is required.

```
curl https://raw.githubusercontent.com/ovk/dotref/master/dotref -o dotref
chmod +x dotref
sudo mv dotref /usr/local/bin
```

# Overview
All `dotref` does is creating and referencing (by using symbolic links) some of the dotfiles (meaning configuration filed or directories).

The main goal is to simplify dotfile management across different machines (e.g. home, work, servers, VMs etc.).
This is done by having different "profiles" for different machines or users.
Profile is simply a JSON file that describes what empty directories to create (if any) and what files/directories to link and where.
Each profile can also have a set of variables that can be used when generating config files from templates.
Profiles are hierarchical and can inherit from one or more profiles.

Simple templating is supported using Python's built-in [templates](https://docs.python.org/3/library/string.html#template-strings).

# Usage
Create a directory which will contain all your dotfiles and other config files.
Inside it, create a `dotref` directory that will contain profiles.

Here is an example of a profile file `home.json` (must be under `dotref` directory):

```json
{
    "extends": [ "base" ],
    "vars": {
        "email": "john.doe@home.com"
    },
    "create": [ "~/downloads", "~/documents" ],
    "link": [
        { "src": "sway", "dst": "~/.config/sway" }
    ]
}
```

The format should be self-explanatory.
The `"extends": [ "base" ]` means that this `home` profile extends from a hypothetical `base` profile which may look like this:

```json
{
    "link": [
        { "src": ".gitconfig", "dst": "~/.gitconfig" }
    ]
}
```

To use templating for `.gitconfig` file just create a `.gitconfig.dotref` file which may look like so:

```
[user]
	email = $email
	name = John Doe
```

`dotref` then will render this `.gitconfig.dotref` file into `.gitconfig` before creating a link `~/.gitconfig` to it.

Note: you can also have a suffix with template files, for example, a `config.dotref.sh` will be also considered a template and rendered to `config.sh`.
This is to keep file extension the same.

To select that `home` profile on a given machine/user run `dotref init --profile home`.
This will remember profile name int he `dotref/.dotref.json` file for all subsequent operations.

To check the status (how the current system state is different from what's in the profile) run `dotref status`.

To bring system to the desired state run `dotref sync`.
This command is idempotent.

To remove all created symlinks run `dotref unlink`.

To view list of profiles run `dotref profiles`.
