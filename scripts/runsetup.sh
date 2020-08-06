export PYTHONBREAKPOINT=ipdb.set_trace
export PYTHONPATH=$PYTHONPATH:src

# execute dev workstation-specific init (like making sure the db is running, etc.)
# FIXME: find out how this is supposed to work but doesn't
# cd "${BASH_SOURCE%/*}"

FILE=.local_setup.sh
if [ -f "$FILE" ]; then
    echo "Found .local_setup.sh file, sourcing"
    source $FILE
fi
