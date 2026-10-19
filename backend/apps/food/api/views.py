from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.food.api.serializers import (
    DeliveryQuoteQuerySerializer,
    DeliveryQuoteSerializer,
    MenuItemInputSerializer,
    MenuItemSerializer,
    NearbyRestaurantSerializer,
    NearbyRestaurantsQuerySerializer,
    OrderCreateSerializer,
    OrderSerializer,
    RestaurantDetailSerializer,
    RestaurantListQuerySerializer,
    RestaurantOrdersQuerySerializer,
    RestaurantProfileSerializer,
    RestaurantSerializer,
)
from apps.food.selectors import (
    find_nearby_restaurants,
    get_order_for_participant,
    get_public_restaurant,
    get_restaurant_for_owner,
    list_customer_orders,
    list_restaurant_orders,
    list_restaurants,
)
from apps.food.services import (
    accept_order,
    add_menu_item,
    approve_restaurant,
    cancel_order,
    close_restaurant,
    delete_menu_item,
    open_restaurant,
    place_order,
    quote_delivery,
    redispatch_order,
    refresh_delivery,
    register_restaurant,
    reinstate_restaurant,
    reject_order,
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


ORDER_ACTION_RESPONSES = {
    200: OrderSerializer,
    404: ErrorSerializer,
    409: ErrorSerializer,
}


class RefreshingOrderListView(ListAPIView):
    serializer_class = OrderSerializer
    pagination_class = DefaultPagination

    def paginate_queryset(self, queryset):
        page = super().paginate_queryset(queryset)
        return [refresh_delivery(order) for order in page]


class OrderListCreateView(RefreshingOrderListView):
    def get_queryset(self):
        return list_customer_orders(user=self.request.user)

    @extend_schema(tags=["food"], operation_id="listMyOrders")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["food"],
        operation_id="placeOrder",
        request=OrderCreateSerializer,
        responses={201: OrderSerializer, 404: ErrorSerializer, 409: ErrorSerializer},
    )
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = place_order(customer=request.user, **serializer.validated_data)
        order = get_order_for_participant(order_id=order.id, user=request.user)
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="getOrder",
        responses={200: OrderSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        order = get_order_for_participant(order_id=pk, user=request.user)
        return Response(OrderSerializer(refresh_delivery(order)).data)


class OrderCancelView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="cancelOrder",
        request=None,
        responses=ORDER_ACTION_RESPONSES,
    )
    def post(self, request, pk: int):
        cancel_order(customer=request.user, order_id=pk)
        order = get_order_for_participant(order_id=pk, user=request.user)
        return Response(OrderSerializer(order).data)


class DeliveryQuoteView(APIView):
    @extend_schema(
        tags=["food"],
        operation_id="quoteDelivery",
        parameters=[DeliveryQuoteQuerySerializer],
        responses={200: DeliveryQuoteSerializer, 404: ErrorSerializer},
    )
    def get(self, request, pk: int):
        query = DeliveryQuoteQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        restaurant = get_public_restaurant(restaurant_id=pk)
        quote = quote_delivery(restaurant=restaurant, **query.validated_data)
        return Response(DeliveryQuoteSerializer(quote).data)


class MyRestaurantOrdersView(RefreshingOrderListView):
    def get_queryset(self):
        query = RestaurantOrdersQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        restaurant = get_restaurant_for_owner(user=self.request.user)
        return list_restaurant_orders(restaurant=restaurant, **query.validated_data)

    @extend_schema(
        tags=["food"],
        operation_id="listRestaurantOrders",
        parameters=[RestaurantOrdersQuerySerializer],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


def _restaurant_order_action(action, operation_id: str):
    class RestaurantOrderActionView(APIView):
        @extend_schema(
            tags=["food"],
            operation_id=operation_id,
            request=None,
            responses=ORDER_ACTION_RESPONSES,
        )
        def post(self, request, pk: int):
            restaurant = get_restaurant_for_owner(user=request.user)
            action(restaurant=restaurant, order_id=pk)
            order = get_order_for_participant(order_id=pk, user=request.user)
            return Response(OrderSerializer(order).data)

    RestaurantOrderActionView.__name__ = (
        f"{operation_id[0].upper()}{operation_id[1:]}View"
    )
    return RestaurantOrderActionView


OrderAcceptView = _restaurant_order_action(accept_order, "acceptOrder")
OrderRejectView = _restaurant_order_action(reject_order, "rejectOrder")
OrderRedispatchView = _restaurant_order_action(redispatch_order, "redispatchOrder")
