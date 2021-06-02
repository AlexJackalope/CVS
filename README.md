# Local CVS (Concurrent Versions System)

This project is a local version system on your computer. You can use it to save different versions of your project that 
you can revert to. At the same time, project versions are not stored as all files from this version, they are stored as 
deltas. This allows you to save multiple versions of the project without clogging the memory with duplicate files and 
their contents.
***

######Developers:
Зайцева Александра 
\
Ловыгин Павел
***

###Arguments:
  #####positional:
  1. CVS command
  2. path to folder with repository
  #####non-positional:
  * -t, --tag: commit tag
  * -c, --comment: just your comment to commit
  * -b, --branchname: branch name


###CVS commands

* ####init
    initializes the repository in an empty folder using the path you entered.
    ```
    C:\Users> C:\Users\...\CVS.py init C:\Users\...\MyRepository
    ```
  
* ####add
    Add all files and changes to the directory by path
    ```
    C:\Users> python C:\Users\...\CVS.py add C:\Users\...\MyRepository
    ```
  
* ####commit
    Commits a change with the specified tag and comment
    ```
    C:\Users> python C:\Users\...\CVS.py commit C:\Users\...\MyRepository -tag new_option_1 -c so_intersting_option
    ```

* ####reset
    Returns to a commit on the branch and cut all next commits. Two ways to call with tag on key with an amount of steps
    back, which is passed by the second argument
    ```
    C:\Users> python C:\Users\...\CVS.py reset C:\Users\...\MyRepository 2
    C:\Users> python C:\Users\...\CVS.py reset C:\Users\...\MyRepository -t version1
    ```
  
* ####switch
    Switches between project versions by tag or forward or backward by current branch
    ```
    C:\Users> python C:\Users\...\CVS.py switch C:\Users\...\MyRepository -2
    C:\Users> python C:\Users\...\CVS.py switch C:\Users\...\MyRepository +1
    C:\Users> python C:\Users\...\CVS.py switch C:\Users\...\MyRepository -t version1
    ```

* ####status
    Gets current state of repository
    ```
    C:\Users\...\MyRepository python C:\Users\...\CVS.py status C:\Users\...\MyRepository
    ```

* ####branch
    Without keys shows list of branches and current with key -b adds a branch
    ```
    #shows list of branches
    C:\Users\...\MyRepository python C:\Users\...\CVS.py branch C:\Users\...\MyRepository
    #adds a branch
    C:\Users\...\MyRepository python C:\Users\...\CVS.py branch C:\Users\...\MyRepository -b branch_name0
    ```

* ####log
    Gets information about commit changes
    ```
    C:\Users\...\MyRepository python C:\Users\...\CVS.py log C:\Users\...\MyRepository
    ```
  
* ####clearlog
    Deletes information about commit changes
    ```
    C:\Users\...\MyRepository python C:\Users\...\CVS.py clearlog C:\Users\...\MyRepository
    ```