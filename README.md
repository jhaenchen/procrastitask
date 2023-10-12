The Procrastinator's Companion is a task management app that aims to mirror my own internal procrastination methodology. It orients around a value system, currently "stress" as a means of prioritizing tasks.

My methodology follows these principles:
* High stress tasks should be completed before low stress tasks.
* Not all tasks have true due dates, and self-imposed due dates don't count.
* Due dates can often be missed. This should be assumed, not penalized.
* That you should do something doesn't mean it's stressful, and we can often be stressed about things we aren't required to do. Stress != importance.
* Tasks change in stressfulness over time. Something that's due soon is more stressful than it was before.

Commands:

n: Create a new task
e4/e1234-5678-9012: Edit the full details of task #4 in the list or the task with the ID 1234-5678-9012
4: View the details of task #4 in the list
d4: Delete (not complete) task #4 in the list
x4: Complete task #4 in the list
r: Refresh stress counts in the order of the least recently updated
w: Help choose a task based on time availability and mental energy to spend
cal4: Create a calendar event for task #4 in the list and open it in my Calendar app

You may configure an alternate location for the storage of your data. This allows you to store the file to a place like Dropbox or iCloud and view it on your phone, since it's just JSON. It also helps you back up your tasks.

To create a custom config:
* Create config.ini next to the Python executable.
In the file:
```
[taks_config]
db_location:/put/a/directory/path/
```