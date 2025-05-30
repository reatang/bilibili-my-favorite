"""
编码处理工具
解决Windows系统下的UTF-8编码问题
"""
import subprocess
import sys
from typing import List, Optional, Union
import locale


def safe_subprocess_run(
    cmd: Union[str, List[str]], 
    capture_output: bool = True, 
    text: bool = True,
    timeout: Optional[int] = None,
    **kwargs
) -> subprocess.CompletedProcess:
    """
    安全的subprocess.run调用，自动处理编码问题
    
    Args:
        cmd: 要执行的命令
        capture_output: 是否捕获输出
        text: 是否以文本模式处理
        timeout: 超时时间
        **kwargs: 其他subprocess.run参数
    
    Returns:
        subprocess.CompletedProcess对象
    """
    # 设置默认编码参数
    if text and 'encoding' not in kwargs:
        kwargs['encoding'] = 'utf-8'
    if text and 'errors' not in kwargs:
        kwargs['errors'] = 'ignore'
    
    # Windows特殊处理
    if sys.platform == 'win32':
        # 确保使用正确的编码
        if 'env' not in kwargs:
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            kwargs['env'] = env
    
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=text,
        timeout=timeout,
        **kwargs
    )


def setup_encoding():
    """
    设置全局编码环境
    在应用启动时调用
    """
    import os
    
    # 设置Python IO编码环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # Windows特殊处理
    if sys.platform == 'win32':
        # 设置Windows控制台相关环境变量
        os.environ['PYTHONUTF8'] = '1'
        
        # 检查控制台是否支持UTF-8
        try:
            # 测试控制台编码能力
            test_string = "测试UTF-8编码"
            test_string.encode('utf-8')
        except UnicodeEncodeError:
            # 如果有编码问题，设置更宽松的错误处理
            os.environ['PYTHONIOENCODING'] = 'utf-8:replace'
    
    # 确保locale设置
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        # 如果系统locale有问题，使用默认
        pass


def safe_decode(data: bytes, encoding: str = 'utf-8') -> str:
    """
    安全解码字节数据
    
    Args:
        data: 要解码的字节数据
        encoding: 目标编码
    
    Returns:
        解码后的字符串
    """
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        encodings = ['gbk', 'gb2312', 'latin1']
        for enc in encodings:
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        
        # 最后的fallback：使用errors='ignore'
        return data.decode(encoding, errors='ignore')


def safe_encode(text: str, encoding: str = 'utf-8') -> bytes:
    """
    安全编码字符串
    
    Args:
        text: 要编码的字符串
        encoding: 目标编码
    
    Returns:
        编码后的字节数据
    """
    try:
        return text.encode(encoding)
    except UnicodeEncodeError:
        return text.encode(encoding, errors='ignore') 