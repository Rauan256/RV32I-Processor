__attribute__((noinline))
int add(int a, int b)
{
    return a + b;
}

int main(void)
{
    volatile int arr[4] = {1, 2, 3, 4};
    int sum = 0;

    for (int i = 0; i < 4; i++) {
        sum = add(sum, arr[i]);
    }

    return sum;
}
