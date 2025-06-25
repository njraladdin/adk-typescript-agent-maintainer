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




ui agent: submit a single commit on a UI, display steps taken by agent on a web ui. list of commits in progress.

troubleshoot: submit a few commits until it can port it perfectly 

hosted : both agent and ui hosted on google cloud 

automatic monitoring: ability to enable monitoring newest commits, check if they were processed yet or not, send them to agent. use sqlite db to track processed commits and retries 

estimated finish : tuesday  
