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

problems: 

agnet is getting confused. make the steps it needs to take tighter and more specific, with examples to make the output much clearer 