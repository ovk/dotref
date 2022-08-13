_dotref()
{
    local cur
    cur="${COMP_WORDS[COMP_CWORD]}"

    if [ $COMP_CWORD -eq 1 ]; then
        COMPREPLY=($(compgen -W '-h --help init sync unlink status profiles version' -- $cur))
    else
        case ${COMP_WORDS[1]} in
            init|sync|unlink|status|profiles)
                _dotref_opt_complete
                ;;
        esac

    fi
}

_dotref_opt_complete()
{
    local cur
    cur="${COMP_WORDS[COMP_CWORD]}"

    if [ $COMP_CWORD -ge 2 ]; then
        case ${COMP_WORDS[COMP_CWORD-1]} in
            -d|--dotdir)
                COMPREPLY=($(compgen -d -- $cur))
                ;;
            -s|--statefile|-p|--profile)
                COMPREPLY=($(compgen -f -- $cur))
                ;;
            *)
                COMPREPLY=($(compgen -W '-v --verbose -s --statefile -d --dotdir -p --profile' -- $cur))
                ;;
        esac
    fi
}

complete -o bashdefault -o default -F _dotref dotref
