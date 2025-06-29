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
- focusedn, simpler : make everything more focused. a lot of stuff here do not need to be seperate agents

hosted : both agent and ui hosted on google cloud 

automatic monitoring: automatically monitor newest commits, send them to agent

TODO: 

- ui : check recent fullstack example, don't use traces, get session events. https://github.com/google/adk-samples/blob/main/python/agents/gemini-fullstack/frontend/src/App.tsx

- process one commit correctly and publish it, starting with this commit : 5b3204c356c4a13a661038cc2a77ebf336d0a112 / https://github.com/google/adk-python/commits/main/?before=f0183a9b98b0bcf8aab4f948f467cef204ddc9d6+455

- battle hardening: process commits until v1.0.0 and troubleshoot issues along the way.
        try claude models 
        include chats of cursor porting commits correctly 
        emulate cursor prompt and tools : https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Cursor%20Prompts/Agent%20Prompt%20v1.0.txt

- simple automatic monitoring 



