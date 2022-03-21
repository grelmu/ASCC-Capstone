# MPPW Setup for Windows with WSL

The MPPW API and UI are containerized for Linux hosts - this means that development on a Windows OS requires either a Linux VM (VirtualBox recommended) or enabling the Windows-Subsystem-for-Linux (WSL).  For Windows 10 and newer, using WSL may be a more seamless route.

## Enable WSL and install Docker Desktop for Windows

The [Docker](https://docs.docker.com/desktop/windows/wsl/) documentation is a great guide to install WSL and Docker Desktop.  Using (Windows) VSCode (also described in the documentation) with WSL support is also recommended.  It's possible to use any Linux IDE in Windows 11 with the WSL GUI integrations, but in Windows 10 it's complex to manage.  VSCode has special support for bridging WSL filesystems without a lot of fiddling around.

It's also recommended to install the Microsoft-developed [Windows Terminal](https://www.microsoft.com/en-ca/p/windows-terminal-preview/9n0dx20hk701) for a much nicer WSL/Powershell/cmd.exe shell experience (with tabs).

At the end of the install, you should be able to run Docker Desktop both in Windows and also in the WSL terminal:

```sh
$ docker container ls
CONTAINER ID   IMAGE                   COMMAND ...
```

## Install SSH Keys in WSL

To access private source code in remote repositories, it's best to use SSH keys - Docker also integrates well with SSH key authentication when building images.  To set up SSH access to a hosted Git repository, first create a user SSH directory and copy your private repository key into the directory:

```sh
$ mkdir ~/.ssh
$ cp <>/id_my_git_ssh_key ~/.ssh/
$ chmod 600 ~/.ssh/id_my_git_ssh_key
```

SSH keys are required to have user-only file permissions - that's the last line above.

In addition to adding the key, a WSL ssh-agent is required to automatically *use* the keys in a Linux system.  On most Linux distributions a (keychain) ssh-agent runs for every user by default, but in WSL this needs to be set up manually.  The right thing to do is install the keychain utility:

```sh
$ sudo apt install keychain
...
```

Next, ensure keychain is running when your WSL terminal starts by editing the `.bashrc` file:

```sh
$ vi ~/.bashrc
(add the following to the end of the file)
eval "$(keychain --eval --quiet)"
```

You'll need to restart your WSL terminal to pick up the change, either in a new terminal or by running:

```sh
$ exec $SHELL
```

At this point, all new WSL terminals will attach to a shared SSH agent:

```
$ ssh-add -L
The agent has no identities.
$ ssh-add ~/.ssh/id_my_git_ssh_key
...
```

... and you'll then be able to checkout private git repositories via git:// URLs.  Also, Docker knows how to use the ssh-agent keys when building images which simplifies container builds using private code.

If you like, you can automatically add the key to the ssh-agent when any WSL terminal starts, making it even easier to use:

```sh
$ vi ~/.bashrc
(add the following to the end of the file)
ssh-add $HOME/.ssh/id_my_git_ssh_key
```

The only downside to this is that it's easier to lose track of what credentials are being used for what codebase if multiple credentials are sometimes used.  Personal preference.

## Install pyenv in WSL

On a Windows development machine we'll want to install [pyenv](https://github.com/pyenv/pyenv-installer) in WSL (also on the Windows side, but not relevant here).  Follow Ubuntu steps [here](https://github.com/pyenv/pyenv/wiki#suggested-build-environment) to `apt-get` prerequisites and then, in the WSL terminal, run:

```sh
$ curl https://pyenv.run | bash
```

The installer will pop up a warning, for whatever reason a final manual step may be needed.  After installing pyenv, in the WSL terminal, run:

```sh
$ vi ~/.bashrc
(add the following to the end of the file)
# pyenv
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"
```

Save, and re-enter your shell (or open a new Terminal tab) so that the bash changes get picked up:

```sh
$ exec $SHELL
$ pyenv version
system (set by ~/.pyenv/version)
```

At this point you have a clean system Python installation - we should try to keep it that way to avoid confusion.

## Install MPPW Python in WSL

In order to install the exact version of Python supported by MPPW, navigate to the MPPW directory and run:

```sh
$ cd <>/material-process-warehouse
$ pyenv install $(cat .python-version)
(python download and install)
$ python --version
Python 3.8.3
```

We'll also want to upgrade pip to the latest version and install the Poetry tools (but nothing else):

```sh
$ python -m pip install --upgrade pip
$ python -m pip install poetry
```

If this is the first time installing this version of Python, you may need to re-navigate to the MPPW directory (or restart your shell) so that pyenv correctly creates the Poetry shims:

```sh
$ cd ..; cd material-process-warehouse
$ poetry --version
```

> NOTE that the steps for installing Python are the same for any codebase once pyenv is installed, and it's only necessary to install a specific version of Python if it's not already installed by pyenv.