import { CircleMinus, CirclePlus } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

type CartDataType = {
  id: string;
  name: string;
  quantity: number;
  price: number;
};

interface ShoppingContextType {
  cartData: CartDataType[];
  cartTotalAmount: number;
  cartTotalItemCount: number;
  addToCart: (itemId: string) => void;
  removeFromCart: (itemId: string) => void;
}

const allShoppingProduct: CartDataType[] = [
  {
    id: "p-01",
    name: "product 01",
    quantity: 0,
    price: 50,
  },
  {
    id: "p-02",
    name: "product 02",
    quantity: 0,
    price: 100,
  },
  {
    id: "p-03",
    name: "product 03",
    quantity: 0,
    price: 150,
  },
];

// 1. create context with a default value
const ShoppingContext = createContext<ShoppingContextType | undefined>(
  undefined
);

const productMap = new Map(allShoppingProduct.map((p) => [p.id, { ...p }]));

// 2. create a context provider
const ShoppingProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [currentCartData, setCurrentCartData] = useState<CartDataType[]>([]);

  const addToCart = useCallback(
    (itemId: string) => {
      const presentInCart = currentCartData.find(
        (product) => product.id === itemId
      );
      const productToAdd = productMap.get(itemId);

      // if the product is not in cart add a fresh order with quantity 1
      if (!presentInCart) {
        productToAdd &&
          setCurrentCartData((prev) => [
            { ...productToAdd, quantity: 1 },
            ...prev,
          ]);
      } else {
        const shoppingCartUpdatedData = currentCartData.map((cartData) => {
          return cartData.id === itemId
            ? {
                ...cartData,
                quantity: (cartData.quantity += 1),
              }
            : cartData;
        });
        setCurrentCartData(shoppingCartUpdatedData);
      }
    },
    [currentCartData]
  );

  const removeFromCart = useCallback(
    (itemId: string) => {
      const presentInCart = currentCartData.find(
        (product) => product.id === itemId
      );

      // if the product is not in cart add a fresh order with quantity 1
      if (!presentInCart) {
        return;
      }
      // when only one quantity is left remove the product
      else if (presentInCart.quantity === 1) {
        const newCartData = currentCartData.filter(
          (cartItem) => cartItem.id !== itemId
        );

        setCurrentCartData(newCartData);
      }
      // if more than 1 quantity of the product is left then decrease the quantity
      else {
        const shoppingCartUpdatedData = currentCartData.map((cartData) => {
          return cartData.id === itemId
            ? {
                ...cartData,
                quantity: (cartData.quantity -= 1),
              }
            : cartData;
        });
        setCurrentCartData(shoppingCartUpdatedData);
      }
    },
    [currentCartData]
  );

  const cartTotalAmount = currentCartData.reduce(
    (total, cartItemData) => total + cartItemData.price * cartItemData.quantity,
    0
  );
  const cartTotalItemCount = currentCartData.reduce(
    (total, cartItemData) => total + cartItemData.quantity,
    0
  );

  const value = useMemo(
    () => ({
      cartData: currentCartData,
      addToCart,
      cartTotalAmount,
      cartTotalItemCount,
      removeFromCart,
    }),
    [currentCartData, addToCart, removeFromCart]
  );

  return (
    <ShoppingContext.Provider value={value}>
      {children}
    </ShoppingContext.Provider>
  );
};

// 3. create a custom hook for using this context
const useShoppingCart = (): ShoppingContextType => {
  const context = useContext(ShoppingContext);

  if (context === undefined) {
    throw new Error("useShoppingCart must be used with a ShoppingProvider");
  }

  return context;
};

// 4. root component
function ShoppingCart() {
  const {
    cartData,
    addToCart,
    removeFromCart,
    cartTotalAmount,
    cartTotalItemCount,
  } = useShoppingCart();

  return (
    <div className="task-container">
      <h2>Task 10: Shopping Cart with Context</h2>

      <div className="task-description">
        <h3>Requirements:</h3>
        <ul>
          <li>Display products list with "Add to Cart" buttons</li>
          <li>Show cart with added items and total price</li>
          <li>Remove items from cart</li>
          <li>Use React Context for cart state</li>
        </ul>
      </div>

      <div className="implementation flex flex-col md:flex-row gap-4">
        {/* product list */}
        <div className="flex flex-col gap-2">
          <h4>Product List</h4>
          {allShoppingProduct.map((prod) => {
            return (
              <div
                key={prod.id}
                className="border rounded-md p-2 flex gap-2 justify-between"
              >
                <div>
                  <p>{prod.name}</p>
                  <p className="opacity-70 text-sm">${prod.price}</p>
                </div>
                <button
                  className="btn btn-secondary h-fit w-fit"
                  onClick={() => addToCart(prod.id)}
                >
                  <CirclePlus />
                </button>
              </div>
            );
          })}
        </div>

        {/* cart list */}
        <div className="flex flex-col border rounded-md">
          <h4 className="bg-background p-2">
            Cart List({cartTotalItemCount} items)
          </h4>
          <div className="flex flex-col gap-2 p-2 divide-y-2">
            {cartData.length === 0 ? (
              <p>Cart is empty</p>
            ) : (
              cartData.map((cartItem) => {
                return (
                  <div
                    key={cartItem.id}
                    className="p-2 flex gap-4 justify-between"
                  >
                    <div>
                      <p>{cartItem.name}</p>
                      <p className="opacity-70 text-sm">
                        ${cartItem.price} x {cartItem.quantity}
                      </p>
                    </div>
                    <div>
                      ${cartItem.price * cartItem.quantity}
                      <button
                        className="btn btn-secondary h-fit w-fit"
                        onClick={() => removeFromCart(cartItem.id)}
                      >
                        <CircleMinus />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
            <div className="p-2 flex justify-between">
              <p className="font-semibold">Total</p>
              <p className="text-text-accent">${cartTotalAmount}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="task-notes">
        <h3>Implementation Notes:</h3>
        <ul>
          <li></li>
        </ul>
      </div>
    </div>
  );
}

export default () => (
  <ShoppingProvider>
    <ShoppingCart />
  </ShoppingProvider>
);
