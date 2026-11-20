"""Conservative names that cannot identify a unique graph endpoint on their own."""
from __future__ import annotations

from vckg.entity_linking.normalize import fold

_GENERIC = {
    "group", "holding", "holdings", "cong ty", "cong ty con", "cong ty con moi",
    "cong ty me", "cong ty lien ket", "cong ty lien doanh", "tap doan", "doanh nghiep",
    "cong ty chung khoan", "cong ty tnhh thuong mai", "ctcp quoc te",
    "cong ty holding", "cong ty phat trien", "bat dong san", "ngan hang dau tu",
    "viet nam", "tai chinh", "dich vu", "benh vien",
    "cong an", "co quan cong an", "cong an tinh", "cong an thanh pho",
    "cong an tp", "cong an huyen", "cong an xa", "co quan canh sat dieu tra",
    "co quan an ninh dieu tra", "co quan dieu tra", "co quan csdt",
    "cuc thue", "cuc thue tinh", "cuc thue thanh pho", "cuc thue tp",
    "chi cuc thue", "chi cuc thue khu vuc",
    "thanh tra", "doan thanh tra", "co quan thanh tra", "thanh tra chung khoan",
    "thanh tra bo", "thanh tra tinh", "thanh tra so",
}


def is_generic_entity(name: str) -> bool:
    """Only exact incomplete phrases; a named province, company or agency remains eligible."""
    return fold(name) in _GENERIC
