"""Task 2 Environment & Hardware Verification Script."""
import sys
import torch

def verify_all():
    print("=== TASK 2: ENVIRONMENT & PYTORCH VERIFICATION ===")
    print("Python Executable:", sys.executable)
    print("Python Version:", sys.version)
    print("PyTorch Version:", torch.__version__)

    # 1. CPU tensor operations
    x_cpu = torch.randn(4, 4)
    y_cpu = torch.matmul(x_cpu, x_cpu)
    print("CPU Matmul Status: SUCCESS, norm =", y_cpu.norm().item())

    # 2. CUDA availability & device name
    cuda_avail = torch.cuda.is_available()
    print("CUDA Available:", cuda_avail)
    if cuda_avail:
        device_name = torch.cuda.get_device_name(0)
        print("CUDA Device Name:", device_name)
        print("CUDA Runtime Version:", torch.version.cuda)
        print("CUDA Device Count:", torch.cuda.device_count())

        # 3. GPU tensor allocation
        x_gpu = torch.randn(1024, 1024, device="cuda:0")
        print("GPU Tensor Allocated Successfully, shape:", x_gpu.shape)

        # 4. GPU matrix multiplication
        y_gpu = torch.matmul(x_gpu, x_gpu)
        torch.cuda.synchronize()
        print("GPU Matmul Status: SUCCESS, norm =", y_gpu.norm().item())

        # 5. Gradient computation
        w = torch.randn(10, 10, device="cuda:0", requires_grad=True)
        loss = (w ** 2).sum()
        loss.backward()
        print("GPU Gradient Computation: SUCCESS, w.grad norm =", w.grad.norm().item())

        # 6. Small optimizer step
        opt = torch.optim.AdamW([w], lr=1e-3)
        opt.step()
        print("GPU Optimizer Step: SUCCESS, updated w norm =", w.norm().item())
        print("STATUS: VERIFIED (GPU + CPU)")
    else:
        print("CUDA is NOT available on this system. Operating in CPU-only mode.")
        print("STATUS: PARTIALLY VERIFIED (CPU ONLY)")

if __name__ == "__main__":
    verify_all()
