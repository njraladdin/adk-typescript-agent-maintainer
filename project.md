# agent : 
- receive commit data - gets commit details and files from python project
- create issue - it creates a issue with a template in typescript project 
- analyze eligibility - checks if commit should be ported 
- handle ineligible commits - close issue with reason, exit 
- port eligible commit - fetches relevant typescript files, and updates each file :
        - fetch file structure: get typescript repo file structure
        - get files: fetch relevant typescript files content using file path
        - update each file: write full updated file and save it locally 

- create PR - submit changes in a PR


# commit-monitor : 
- fetch recent commits 
- get existing issues 
- filter unprocessed commits (and only keep the oldest one)
- send to agent 



progress: 
- coder context gatherer agent is working.
- coder writes code based on context 
- agent workspace: clone repo and setup project in agent workspace (not by agent, before agent callback)
- use vertex: use vertex gemini api with credits instead of free aistudio api 
- validate: update files, build project, run tests and iterate  
- manage repo : create issue (and close), create branch, use coder agent, submit PR
- generating good code: reduce unnecessary python context, focused typescript context 
- limit number of tries for code writer. if stil lfail after all retries, delete issue 
- ability to fetch another file in code translation agent 
- always start with fresh cloned repo 
- ui agent: submit a single commit on a UI, display steps taken by agent on a web ui.


focused and simpler : make everything more focused. a lot of stuff here doesn't need to be part of agent, just simple workflow to run before or after the agent 

        the context agent doesnt need to fetch the repos structures and commit information and get file content of each changed file.  should be a before agent callback. main goal is to decide which relevant typescirpt fiels to fetch based on repo file sturctures and commit diff and updated files 

        make it able to fetch more files at once, saves time for faster testing OR feed all files to gemini flash lite and output list of relevant files 

        for maintainer agent, most steps doesnt require an agent, but simple flow in before agent callback (or a single function by the agent). simplify.

        after simplifying the 3 agents in project, see what can be merged while staying easily testable 


troubleshoot: submit a few commits until it can port it perfectly:

hosted : both agent and ui hosted on google cloud 

automatic monitoring: automatically monitor newest commits, send them to agent

