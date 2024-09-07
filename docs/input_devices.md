# Input devices

## Kinesis Advantage 360

Reference:

- https://kinesis-ergo.com/support/kb360/
- https://kinesis-ergo.com/wp-content/uploads/Advantage360-SmartSet-KB360-Users-Manual-v10-12-22.pdf
- https://kinesis-ergo.com/wp-content/uploads/Adv360-SmartSet-Direct-Programming-Guide-v12-2-22.pdf
- https://kinesis-ergo.com/wp-content/uploads/Adv360-SmartSet-Direct-Programming-Action-Tokens-v3-31-23.pdf

Steps:

- access the Direct Programming mode using the `SmartSet`+`V-Drive` keys
- place the custom configuration below in `layouts/layout6.txt` and save the file
- eject the drive and press the `SmartSet`+`V-Drive` keys
- if that fails and the keyboard isn't responsive, disconnect the keyboard cable and reconnect it

```text
<base>
[hk1]>[prnt]
{hk2}>{-lshf}{prnt}{+lshf}
{hk3}>{x1}{keyt}{-rwin}{-lalt}{kp0}{+rwin}{+lalt}
{hk4}>{x1}{keyt}{-rwin}{-lshf}{kp0}{+rwin}{+lshf}

<keypad>

<function1>
[left]>[vol-]
[rght]>[vol+]
[rwin]>[lwin]
{up}>{-rwin}{pgup}{+rwin}
{down}>{-rwin}{pgdn}{+rwin}
{lshf}{up}>{-rwin}{-lshf}{pgup}{+rwin}{+lshf}
{lshf}{down}>{-rwin}{-lshf}{pgdn}{+rwin}{+lshf}

<function2>

<function3>
```
