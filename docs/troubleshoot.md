## Troubleshooting

### Docker: permission denied

```
permission denied while trying to connect to the Docker API
at unix:///var/run/docker.sock
```

---

### Step 1

```
## before
$ grep docker /etc/group
                                      ← no output, group doesn't exist

## after
$ sudo groupadd docker

$ grep docker /etc/group
docker:x:999:                          ← group exists now
```

---

### Step 2

```
## before
$ groups
ubuntu adm cdrom sudo dip lxd          ← docker missing, not in group

## after
$ sudo usermod -aG docker ubuntu
$ newgrp docker

$ groups
docker adm cdrom sudo dip lxd ubuntu   ← docker now appears, you're in the group
```

---

### Step 3

```
## before
$ ls -l /var/run/docker.sock
srw------- 1 root root 0 Jun  2 10:00 /var/run/docker.sock   ← wrong owner/group

## after
$ sudo chown root:docker /var/run/docker.sock
$ sudo chmod 660 /var/run/docker.sock

$ ls -l /var/run/docker.sock
srw-rw---- 1 root docker 0 Jun  2 10:00 /var/run/docker.sock   ← correct now
```

---

### Verify

```
$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS   NAMES
```
