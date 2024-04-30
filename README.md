# Network Troubleshooter for Laymen
This is a WIP network troubleshooter *for Windows only*. I figure that someone who's using Linux is outside the target audience for this program. It's also relies heavily on the operating system.

### Goal
I wanted to make something that I my family could run while I'm away that would fix or detect a number of issues, or even just narrow it down for me. My family is reasonably competent with computers, but they aren't tech people. They'd have difficulty doing a methodical troubleshooting of the network. However, guided fixes like ensuring the little flashing lights on the Ethernet port (yes, I know what they're actually called) are perfect for them.

I also wanted it to be able to generate a log file that they could somehow send to me, allowing me to get all the details for the tests it ran, including things like the output of the commands, and interactions with the user.

### Information Gathering
*Almost* all information currently gathered is from parsing the output of commands. The main commands used are `ping`, `ipconfig`, and `Get-NetAdapter` (from PowerShell). I was originally just using `wmic`, but I realized that it's deprecated and wasn't working for me, so I started using PowerShell.

### Future Improvements
It is not done, and I'm not sure when I'll have the time to complete it, but there are a number of things I want to improve with it.
- It requires the user to install Python and a library or two, Which is a big ask, given the target audience. I want to make a Batch script that will download a portable Python installation and the required libraries, as well as a Batch script to run the Python script.
- The above must be done ahead of time, when they're not having an issue. Of course, this isn't an avoidable problem, but making it as portable as possible (e.g. on a flash drive) will make it easier.
- Improve the control flow structure. It's something of a mess right now, but in part because I don't know how to make it better.
- Implement more tests and checks.
