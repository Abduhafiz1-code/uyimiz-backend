from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from listings.models import Contract
from .models import Rating, RatingTarget
from .serializers import RatingSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_contract_view(request, pk):
    """Bitim yopilgach — xaridor agentni/sotuvchini, sotuvchi xaridorni baholaydi."""
    contract = Contract.objects.filter(pk=pk).select_related('listing', 'seller', 'buyer', 'agent').first()
    if not contract:
        return Response({'error': 'not_found'}, status=status.HTTP_404_NOT_FOUND)
    if contract.status != 'signed':
        return Response({'error': "Shartnoma hali imzolanmagan"}, status=status.HTTP_400_BAD_REQUEST)
    if request.user.id not in (contract.seller_id, contract.buyer_id):
        return Response({'error': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

    score = request.data.get('score')
    comment = request.data.get('comment', '')
    is_buyer = request.user.id == contract.buyer_id

    if is_buyer:
        target_type = RatingTarget.AGENT if contract.agent_id else RatingTarget.OWNER
        target_user = contract.agent if contract.agent_id else contract.seller
    else:
        target_type = RatingTarget.OWNER
        target_user = contract.buyer

    serializer = RatingSerializer(data={
        'target_type': target_type, 'target_user': target_user.id,
        'target_listing': contract.listing_id, 'contract': contract.id,
        'score': score, 'comment': comment,
    })
    serializer.is_valid(raise_exception=True)
    rating = serializer.save(rater=request.user)

    target_user.apply_rating(rating.score)
    if target_type != RatingTarget.OWNER or True:
        listing = contract.listing
        total = listing.rating_avg * listing.rating_count + rating.score
        listing.rating_count += 1
        listing.rating_avg = round(total / listing.rating_count, 1)
        listing.save(update_fields=['rating_avg', 'rating_count'])

    return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_ratings_view(request, pk):
    items = Rating.objects.filter(target_user_id=pk).select_related('rater')
    return Response(RatingSerializer(items, many=True).data)
