# dsController
Controls dialog

## Installation
1. Clone/download repo to anywhere on your machine
2. Create **dsController.mod** in *documents/maya/modules*
3. Add the following lines to it:

```python
+ dsController 0.0.1 YourPathHere/dsController
scripts: YourPathHere/dsController
```

4. Run the following python command to show tool window:
```python
import dsController
dsController.MainWindow.display()
```
