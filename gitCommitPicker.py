############################################################################
#                                                                          #
# Assuming current branch is always cherry-picking or rebasing from master #
# Use this tool to pick specific commits from master                       #
# Will automatically rebase on master when possible                        #
#                                                                          #
############################################################################
#                                                                          #
# How to use:                                                              #
# 1. Switch to the branch you want to pick commits to                      #
# 2. Run this script in CMD with the git directory path as first argument  #
#    Or simply drag the git folder to this script to open it               #
# 3. Follow the instructions and paste the master commits you want to pick #
# 4. Check the result and push if no problems found                        #
#                                                                          #
############################################################################

# python version: 3.9.2
# author: MaugouMio
# date: 2023/10/2

import sys, os, time

try:
	import git
except:
	os.system("pip3 install GitPython")
	import git

try:
	repo = git.Repo(sys.argv[1])
except git.exc.InvalidGitRepositoryError:
	print("Current directory is not an available git repository!")
	sys.exit(1)
	
branch = repo.active_branch
print("\n==================================")
print("\n Current branch:", branch.name, "\n")
print("==================================\n")

input("<Press enter if this is the target branch>\n")

# the branching point of current branch
baseCommit = repo.merge_base(branch.name, "master")

# get master new commits
commitRange = f"{baseCommit[0]}..master"
masterCommits = []
for commit in repo.iter_commits(rev=commitRange, first_parent=True):
	if commit == baseCommit:
		break
	masterCommits.insert(0, commit)

# for checking whether a master commit is picked or not
picked = set()

# mark already cherry-picked commits
commitRange = f"{baseCommit[0]}..{branch.name}"
for commit in repo.iter_commits(rev=commitRange):
	if commit == baseCommit:
		break
		
	message = commit.message.split('\n')
	if len(message) > 2:  # message structure be like ['Title', 'Description line1', 'Description line2', ..., '']
		if message[-2][:27] == "(cherry picked from commit ":  # cherry-picked note is always in this format and at the last line of description
			picked.add(message[-2][27:-1])  # line format: (cherry picked from commit {TARGET_SHA})



# get user specify commits
targetCommits = set()
print("")
print("")
print("Note:")
print('1. Spaces and `"` will be stripped.')
print('2. Enter "end" to stop entering commits.')
print("=======================================")
print("Enter commit SHA line by line below:\n")
while True:
	sha = input().lstrip(' "').rstrip(' "')
	if len(sha) == 0:
		continue
	if sha == "end":
		break
	targetCommits.add(sha)

print("")
print("Commits specified! Checking for lost commits...")
print("")



# search for lost commits (commits that must be picked but not in the list)
lostCommits = []
skippedCommits = []
affectedFiles = set()
for i in range(len(masterCommits) - 1, -1, -1):
	commit = masterCommits[i]
	sha = commit.hexsha
	if sha not in targetCommits and sha not in picked:
		needInclude = commit.message.startswith("Merge branch 'master'")  # Auto Merge commit must be picked
		if not needInclude:  # commits that have modified any of the files in the newer commits must be picked
			for file in commit.stats.files.keys():
				if file in affectedFiles:
					needInclude = True
					break
		
		if needInclude:
			lostCommits.append(commit)
			targetCommits.add(sha)
	else:
		needInclude = True
	
	if needInclude:
		for file in commit.stats.files.keys():
			affectedFiles.add(file)
	else:
		skippedCommits.append(commit)
	
	print(f"Checking master commits ({len(masterCommits) - i}/{len(masterCommits)})")

if len(lostCommits) > 0:
	print("The following commits will be picked but NOT in the list.")
	print("If some of these should not appear in this version, you have to turn it off by game logic.")
	print("=======================================================")
	for commit in lostCommits:
		print(commit.message[:commit.message.find('\n')].encode("big5").ljust(95).decode("big5"), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(commit.committed_date)),
			f"\n        Author: {commit.author.name}".ljust(70), "sha:", commit.hexsha)
	input("\n<Press Enter to continue>\n")
else:
	print("No lost commits found!")

if len(skippedCommits) > 0:
	print("\nThe following commits on master are still not picked.")
	print("Please make sure you really don't want them picked now, or you just forgot it.")
	print("=======================================================")
	for commit in skippedCommits:
		print(commit.message[:commit.message.find('\n')].encode("big5").ljust(95).decode("big5"), time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(commit.committed_date)),
			f"\n        Author: {commit.author.name}".ljust(70), "sha:", commit.hexsha)
	input("\n<Press Enter to continue>\n")



print("")
print("Start processing...")
print("")

# iterate through master commit list and check whether to pick or not
canRebase = True
rebaseCommit = None
i = 1
for commit in masterCommits:
	sha = commit.hexsha
	if sha in picked:
		print(f"Commit already picked ({i}/{len(masterCommits)})")
		if canRebase:
			rebaseCommit = commit
	elif sha in targetCommits:
		if canRebase:
			print(f"Commit can be rebased ({i}/{len(masterCommits)})")
			rebaseCommit = commit
		else:
			print(f"Picking commit {sha} ({i}/{len(masterCommits)})")
			if commit.message.startswith("Merge branch"):
				repo.git.execute(f"git cherry-pick -x -m 1 {sha}")  # don't know why repo.git.cherry_pick("-x -m 1", sha) shows error...
			else:
				repo.git.cherry_pick("-x", sha)
		targetCommits.remove(sha)  # mark for checking if there are some specific commits not picked
	else:  # skipped commit, can not rebase after this
		if canRebase and rebaseCommit:
			print(f"Found skipped commit, start rebasing on {rebaseCommit.hexsha} ({i}/{len(masterCommits)})")
			repo.git.rebase(rebaseCommit.hexsha)
		else:
			print(f"Commit skipped ({i}/{len(masterCommits)})")
		canRebase = False
	i += 1

print("")
if rebaseCommit:
	if canRebase:  # didn't found any skipped commit, rebase on the newest one
		repo.git.rebase(rebaseCommit.hexsha)
	print("")
	print("")
	print(f"# Rebased on {rebaseCommit}")
	print("# %s\n\n" %rebaseCommit.message.split('\n')[0])  # commit title

if len(targetCommits) > 0:
	print("Warning:")
	print("The following commits specified are not picked.")
	print("It's most likely that they were already picked before, or were part of another Merge commits.")
	print("=======================================================")
	for sha in targetCommits:
		print(sha)
else:
	print("Commits picked successfully!")
	print("Check the result using your git GUI tools and push them if no problems found.\n")
	
os.system("pause")
