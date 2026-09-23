# Task 4.1: Docker environment setup (Pass)

No code for this level, just these commands:

```powershell
wsl --version
docker --version
docker version
docker login
docker pull hello-world
docker run --name hello-4-1 hello-world
docker ps -a --filter "name=hello-4-1"
docker images hello-world
```

`.\scripts\task4.1-hello-world.ps1` (from the repo root) runs the same commands and saves the output to `logs\task4.1-hello-world.log`.
