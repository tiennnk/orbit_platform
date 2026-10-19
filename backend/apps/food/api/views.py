from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.food.api.serializers import (
    MenuItemInputSerializer,
    MenuItemSerializer,
    NearbyRestaurantSerializer,
    NearbyRestaurantsQuerySerializer,
    RestaurantDetailSerializer,
    RestaurantListQuerySerializer,
    RestaurantProfileSerializer,
    RestaurantSerializer,
)
from apps.food.selectors import (
    find_nearby_restaurants,
    get_public_restaurant,
    get_restaurant_for_owner,
    list_restaurants,
)
from apps.food.services import (
    add_menu_item,
    approve_restaurant,
    close_restaurant,
    delete_menu_item,
    open_restaurant,
    register_restaurant,
    reinstate_restaurant,
    reject_restaurant,
    suspend_restaurant,
    update_menu_item,
    update_restaurant_profile,
)
from apps.shared.pagination import DefaultPagination
from apps.shared.serializers import ErrorSerializer

ACTION_RESPONSES = {
    200: RestaurantSerializer,
    404: ErrorSerializer,
    409: ErrorSerializer,
}


class RestaurantListCreateView(ListAPIView):
    serializer_class = RestaurantSerializer
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        query = RestaurantListQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return list_restaurants(**query.validated_data)

    @extend_schema(
        tags=["admin"],
        operation_id="listRestaurants",
        parameters=[RestaurantListQuerySerializer],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["food"],
        operation_id="registerRestaurant",
        request=RestaurantProfileSerializer,
        responses={201: RestaurantSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = RestaurantProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = register_restaurant(
            owner=request.user, **serializer.validated_data
        )
        return Response(
            RestaurantSerializer(restaurant).data, status=status.HTTP_201_CREATED
        )


class MyRestaurantView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="getMyRestaurant",
        responses={200: RestaurantDetailSerializer, 404: ErrorSerializer},
    )
    def get(self, request):
        restaurant = get_restaurant_for_owner(user=request.user)
        return Response(RestaurantDetailSerializer(restaurant).data)

    @extend_schema(
        tags=["food"],
        operation_id="updateMyRestaurant",
        request=RestaurantProfileSerializer,
        responses=ACTION_RESPONSES,
    )
    def put(self, request):
        serializer = RestaurantProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = get_restaurant_for_owner(user=request.user)
        restaurant = update_restaurant_profile(
            restaurant_id=restaurant.id, **serializer.validated_data
        )
        return Response(RestaurantSerializer(restaurant).data)


class MyRestaurantOpenView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="openMyRestaurant",
        request=None,
        responses=ACTION_RESPONSES,
    )
    def post(self, request):
        restaurant = get_restaurant_for_owner(user=request.user)
        restaurant = open_restaurant(restaurant_id=restaurant.id)
        return Response(RestaurantSerializer(restaurant).data)


class MyRestaurantCloseView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="closeMyRestaurant",
        request=None,
        responses=ACTION_RESPONSES,
    )
    def post(self, request):
        restaurant = get_restaurant_for_owner(user=request.user)
        restaurant = close_restaurant(restaurant_id=restaurant.id)
        return Response(RestaurantSerializer(restaurant).data)


class MyMenuView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="addMenuItem",
        request=MenuItemInputSerializer,
        responses={201: MenuItemSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = MenuItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = get_restaurant_for_owner(user=request.user)
        item = add_menu_item(restaurant=restaurant, **serializer.validated_data)
        return Response(MenuItemSerializer(item).data, status=status.HTTP_201_CREATED)


class MyMenuItemView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="updateMenuItem",
        request=MenuItemInputSerializer,
        responses={200: MenuItemSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def put(self, request, pk: int):
        serializer = MenuItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = get_restaurant_for_owner(user=request.user)
        item = update_menu_item(
            restaurant=restaurant, item_id=pk, **serializer.validated_data
        )
        return Response(MenuItemSerializer(item).data)

    @extend_schema(
        tags=["food"],
        operation_id="deleteMenuItem",
        responses={204: None, 404: ErrorSerializer},
    )
    def delete(self, request, pk: int):
        restaurant = get_restaurant_for_owner(user=request.user)
        delete_menu_item(restaurant=restaurant, item_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NearbyRestaurantsView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="findNearbyRestaurants",
        parameters=[NearbyRestaurantsQuerySerializer],
        responses=NearbyRestaurantSerializer(many=True),
    )
    def get(self, request):
        query = NearbyRestaurantsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        restaurants = find_nearby_restaurants(
            latitude=data["latitude"],
            longitude=data["longitude"],
            radius_km=data["radius_km"],
            limit=data["limit"],
            query=data["q"].strip(),
        )
        return Response(NearbyRestaurantSerializer(restaurants, many=True).data)


class RestaurantDetailView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="getRestaurant",
        responses={200: RestaurantDetailSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        restaurant = get_public_restaurant(restaurant_id=pk)
        return Response(RestaurantDetailSerializer(restaurant).data)


def _admin_action(action, operation_id: str):
    class AdminActionView(APIView):
        permission_classes = [IsAdminUser]

        @extend_schema(
            tags=["admin"],
            operation_id=operation_id,
            request=None,
            responses=ACTION_RESPONSES,
        )
        def post(self, request, pk: int):
            restaurant = action(restaurant_id=pk)
            return Response(RestaurantSerializer(restaurant).data)

    AdminActionView.__name__ = f"{operation_id[0].upper()}{operation_id[1:]}View"
    return AdminActionView


RestaurantApproveView = _admin_action(approve_restaurant, "approveRestaurant")
RestaurantRejectView = _admin_action(reject_restaurant, "rejectRestaurant")
RestaurantSuspendView = _admin_action(suspend_restaurant, "suspendRestaurant")
RestaurantReinstateView = _admin_action(reinstate_restaurant, "reinstateRestaurant")
