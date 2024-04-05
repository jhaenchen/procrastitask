The Procrastinator's Companion is a smart task manager.

It looks similar to other to-do list managers you may have used before, but it is crucially different in its mathematical ranking function for helping you choose what you should do next. This is a critical difference; tasks vary dramatically in their timeframe, their value to you over that time, their difficulty, and their attributive characteristics. In the modern existence, many of us accept the idea that the list will never go away, we will never eliminate every task. This list operates that way. It will help you keep track of short term, long term, and periodic tasks in your life. It will help you manage your life according to your priorities, e.g. I tend to complete things stressing me before I complete tasks that are self-investments in my long-term joy. My list ranking automatically reflects this preference. It is not complicated to use, it does not hide behind a fancy interface. It aims to be a representative of your own brain, your own ranking preferences. In the same way your list of things to do changes throughout the day and year, or tasks move up and down based on the passage of time or on dependencies, this app will do the same, allowing tasks to flow up and down based on mathematical functions you use to describe a task's value to you.

Features:

* Create, edit, complete, and delete tasks
* Due dates
* Dependent tasks
* Task selection wizard
* Calendar integration (mac)
* Dynamic functional priorities
* "Smart" ranking (or Multi-unit priority coordinate ranking system)
* Dropbox backup support
* Automatic priority refresh detection


How to Run:

1. Clone the git repository
2. In the repository folder, run `pip install`
3. Run the app `python procrastitask.py`

You'll be presented with the command screen.

Commands (enter the command and hit enter):

```
save: save changes
load: reload tasks
n: Create a new task
e4 OR e1234-5678-9012: Edit the full details of task #4 in the list or the task with the ID 1234-5678-9012
4: View the details of task #4 in the list
d4: Delete (not complete) task #4 in the list
x4: Complete task #4 in the list
r: Refresh stress counts in the order of the least recently updated
w: Help choose a task based on time availability and mental energy to spend
cal4: Create a calendar event for task #4 in the list and open it in my Calendar app
nn: Create a new task using vim to enter the details
n3: Create a task that depends on task [3] being completed first
p3: Create a task that task [3] depends on being completed first
```

Let's walk through creating a task. I'll hit the key `n` and then hit the enter key.

```
Title: // This can be whatever you want for the title of your task
Description: // Optional, add additional details here. Leave blank if you want.
Due Date: // Always optional, but uses a special format: (`4` means the soonest 4th day of the month coming up, `4.12` means december 4th)
Difficulty: // Required integer, how hard is this to actually execute and complete?
Stress: // How worried are you about this task? How much anxiety is it giving you?
Duration: // How long, in minutes, will it take to complete this task?
Dependent On: // Optional, are any tasks required before this one? (You can pass a list index from the home view like `4` or get the full ID of the task by viewing its details)
Increase every x days: // Optional integer, increase the stress value every X days
Cool down: // Optional string, after completion, bring this task back after X, (Xmin, Xd, Xw, Xm) 
Periodicity: // Optional, task comes back at a time, cron syntax
```

After entering these details, we'll see our task in the list. We should hit `s` and `enter` to save this new task.

### Details on the ranking system
The list is sorted first by stress, then by difficulty. However, there are various modifiers that can affect where a task ends up in the rank.

* If a task is due "soon" (aka 2 days for every hour of effort), it will receive a bonus in priority of 1/3 of its original stress value
* If you specify a linear increase dynamic via the "Increase every x days" field, the stress (priority) will increase periodically


### Backup your database elsewhere:

You may configure an alternate location for the storage of your data. This allows you to store the file to a place like Dropbox or iCloud and view it on your phone, since it's just JSON. It also helps you back up your tasks.

To create a custom config:
* Create config.ini next to the Python executable.
In the file:
```
[taks_config]
db_location:/put/a/directory/path/
```

### Future features:

* More dynamics: linear-with-cap, gaussian, gaussian-with-shelf, peak-at-due-time
* Multi coordinate support (joy, stress, love, etc, these should all be units in our list of life)
