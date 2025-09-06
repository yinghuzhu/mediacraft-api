"""
Core utility functions for MediaCraft backend
"""

def get_client_ip(request):
    """获取客户端真实IP地址"""
    # 优先使用 X-Real-IP 头部（Nginx 设置）
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    # 其次使用 X-Forwarded-For 头部（可能包含多个IP）
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # X-Forwarded-For 可能包含多个IP，第一个是原始客户端
        return forwarded_for.split(',')[0].strip()
    
    # 最后使用直接连接的IP（通常是代理服务器）
    return request.remote_addr or 'unknown'