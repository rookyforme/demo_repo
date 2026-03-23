# 俄罗斯方块（Python）

提供两个版本：

- `main.py`：使用标准库 `tkinter` 实现（不依赖第三方包）
- `main_pygame.py`：使用 `pygame` 实现（需要第三方包）

## 运行

tkinter 版本（`main.py`）直接运行：

```bash
python3 main.py
```

pygame 版本（`main_pygame.py`）运行前需要安装依赖：

```bash
source venv/bin/activate
pip install pygame
python main_pygame.py
```

键位说明：

- `←` / `→`：左右移动
- `↑`：旋转
- `↓`：软降（按一下下降一步）
- `Space`：硬降
- `P`：暂停/继续
- `R`：重新开始
- `Esc`：退出
