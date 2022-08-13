set -l commands -h --help init sync unlink status profiles version

set -l h -s h -l help      -d 'Print help message and exit'
set -l v -s v -l verbose   -d 'Produce more verbose output'
set -l d -s d -l dotdir    -d 'Directory containing profiles' -rF
set -l s -s s -l statefile -d 'Dotref state file' -rF
set -l p -s p -l profile   -d 'Name of the profile to use' -rF

complete -c dotref -f

complete -c dotref -n "not __fish_seen_subcommand_from $commands" -a "$commands"

for line in 'init:     p d s v' \
            'sync:     d s v'   \
            'unlink:   d s v'   \
            'status:   d s v'   \
            'profiles: p d v'
    set -l command (echo "$line" | cut -d: -f1)

    for opt in (echo "$line" | cut -d: -f2 | string split -n ' ')
        complete -c dotref -n "__fish_seen_subcommand_from $command" $$opt
    end
end
