from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Contest


class ContestFeed(Feed):
    """대회 RSS 피드"""
    title = "배드민톡 - 전국 배드민턴 대회"
    link = "/badminton-tournament/"
    description = "배드민톡 전국 배드민턴 대회 정보"
    
    def items(self):
        """최신 대회 20개"""
        return Contest.objects.select_related('category', 'sponsor').order_by('-created_at')[:20]
    
    def item_title(self, item):
        """대회 제목"""
        return item.title
    
    def item_description(self, item):
        """대회 설명"""
        description_parts = []
        
        if item.get_period_display():
            description_parts.append(f"대회 기간: {item.get_period_display()}")
        
        if item.get_registration_period_display():
            description_parts.append(f"접수 기간: {item.get_registration_period_display()}")
        
        if item.get_location_display():
            description_parts.append(f"장소: {item.get_location_display()}")
        
        if item.description:
            description_parts.append(item.description[:150])
        
        return " | ".join(description_parts) if description_parts else ""
    
    def item_link(self, item):
        """대회 상세 URL"""
        return reverse('contests:detail', args=[item.slug])
    
    def item_pubdate(self, item):
        """대회 등록일"""
        return item.created_at

