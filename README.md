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
* Location-based dynamic

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
created: List the tasks that were most recently created
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
Location: // Optional, specify a location to adjust stress based on your current location
```

After entering these details, we'll see our task in the list. We should hit `s` and `enter` to save this new task.

### Details on the ranking system
The list is sorted first by stress, then by difficulty. However, there are various modifiers that can affect where a task ends up in the rank.

* If a task is due "soon" (aka 2 days for every hour of effort), it will receive a bonus in priority of 1/3 of its original stress value
* If you specify a linear increase dynamic via the "Increase every x days" field, the stress (priority) will increase periodically
* If you specify a location-based dynamic, the stress will be adjusted based on your current location


### Backup your database elsewhere:

You may configure an alternate location for the storage of your data. This allows you to store the file to a place like Dropbox or iCloud and view it on your phone, since it's just JSON. It also helps you back up your tasks.

To create a custom config:
* Create config.ini at the top level of this project, next to this README file, for example.
In the file:
```
[taks_config]
db_location:/put/a/directory/path/
```

## Task Features & Capabilities

A task in Procrastitask supports a wide range of features to help you manage your work and priorities:

- **Basic Properties**:
  - **Title**: The name of your task.
  - **Description**: Optional details about the task.
  - **Difficulty**: Integer value representing how hard the task is to complete.
  - **Stress**: Integer value for how much anxiety or urgency the task causes.
  - **Duration**: Estimated time (in minutes) to complete the task.
  - **List Name**: Organize tasks into different lists.

- **Due Dates & Scheduling**:
  - **Due Date**: Set a specific due date for the task.
  - **Due Date (Cron)**: Use cron syntax to set recurring due dates (e.g., every Monday).
  - **Periodicity**: Use cron syntax to make a task repeat at regular intervals. The task will become incomplete again at each interval.
  - **Cool Down**: After completion, the task will reappear after a specified cooldown (e.g., 2d, 1w, 30min).

- **Completion & History**:
  - **Mark Complete/Incomplete**: Mark tasks as complete or incomplete. Tasks with periodicity or cooldowns can become incomplete again automatically.
  - **Completion History**: Each completion is recorded with a timestamp and stress value at completion.
  - **Automatic Status**: Task status updates automatically based on periodicity, cooldown, and completion history.

- **Dynamic Stress & Ranking**:
  - **Dynamic Stress**: Attach a dynamic function to a task to make its stress value change over time (e.g., increase every X days, location-based, or custom dynamics).
  - **Smart Ranking**: Tasks are ranked by stress, difficulty, and due date proximity. Due soon tasks get a stress bonus.

- **Dependencies**:
  - **Dependent On**: Specify other tasks that must be completed before this one.
  - **Dependents**: See which tasks depend on the current task.
  - **Dependency Checks**: Tasks can only be completed if their dependencies are complete.

- **Calendar Integration**:
  - **Create Calendar Event**: Instantly create and open a calendar event for a task (macOS only).

- **Other Features**:
  - **Location-Based Dynamics**: Adjust stress based on your current location.
  - **Automatic Refresh**: Task priorities and stress values refresh automatically based on time and completion.
  - **Custom Config & Backup**: Store your task database in a custom location (e.g., Dropbox, iCloud).

See below for details on commands and how to use these features in practice.

---

### Future features:

* More dynamics: linear-with-cap, gaussian, gaussian-with-shelf, peak-at-due-time
* Multi coordinate support (joy, stress, love, etc, these should all be units in our list of life)


### Development

To run procrastitask:

```
pipenv shell
pipenv install
python procrastitask.py
```

To run unit tests:

```
pipenv shell # if not already active
pipenv install --dev
pytest
```

To generate coverage:

```
pipenv shell # if not already active
pipenv install --dev
coverage run -m pytest
coverage html # open index.html within htmlcov directory
```
