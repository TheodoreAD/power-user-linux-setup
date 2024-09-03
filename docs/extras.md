# Extras

!!! WARNING
    Optional.

## Fix CRLF

```shell
# find . -type f | xargs file -k -- | grep CRLF | wc -l
# find . -type f | xargs dos2unix
# chmod go-w -R *
# sudo find . -type f | xargs chmod a-x
```
