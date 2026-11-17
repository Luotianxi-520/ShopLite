"""全局 pytest 选项."""


def pytest_addoption(parser):
    parser.addoption(
        "--headed",
        action="store_true",
        default=False,
        help="UI 测试使用有界面 Edge 运行,便于观察自动化执行过程",
    )
    parser.addoption(
        "--slow",
        nargs="?",
        const=1.0,
        default=0.0,
        type=float,
        metavar="SECONDS",
        help="演示模式:每个浏览器操作后停顿 N 秒(默认 1 秒),需配合 --headed",
    )
