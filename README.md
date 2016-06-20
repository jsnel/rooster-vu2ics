# rooster-vu2ics
Simple tool to convert VU html/text course schedule info into an ICS format for import into e.g. google calendar

From rooster.vu.nl, open your favourite coure(s). Be sure to select the 'per week' view. In the schedule view page, select all text (<ctrl+a> should work in most cases) and past this into a text file. Feed this as input, the output should be an i-cal (.ics) file. You can concatenate multiple such files as input, which should nicely deal with duplicates that you might get from multiple selections (e.g., selecting on docent and on student group).

The script requires pyton, but should be fairly independent of the version (the syntax is not compatible with python 3).
