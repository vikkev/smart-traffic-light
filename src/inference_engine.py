"""
InferenceBackend: Abstração de hardware para detecção YOLO.
Detecta e usa GPU (CUDA/MPS) se disponível; fallback automático para CPU.
 
Uso:
    backend = InferenceBackend('yolov8s.pt', force_cpu=False)
    results = backend.track(frame, persist=True, conf=0.4)
"""
 
import logging
import sys
 
logger = logging.getLogger(__name__)
 
 
class InferenceBackend:
    """
    Abstração agnóstica de hardware para YOLO.
    
    Detecta automaticamente:
    - GPU NVIDIA (CUDA)
    - GPU Apple (Metal Performance Shaders)
    - Fallback para CPU
    
    Permite forçar CPU mesmo se GPU disponível.
    """
    
    def __init__(self, model_path, force_cpu=False):
        """
        Inicializa backend de inferência.
        
        Args:
            model_path (str): Caminho para arquivo .pt do YOLO
            force_cpu (bool): Se True, força uso de CPU
        
        Raises:
            FileNotFoundError: Se model_path não existe
            ImportError: Se torch não está instalado
        """
        self.model_path = model_path
        self.model = None
        self.device = None
        
        # Detectar device
        self.device = self._detectar_device(force_cpu)
        logger.info(f"Device selecionado: {self.device}")
        
        # Carregar modelo
        self._carregar_modelo()
        logger.info(f"Backend YOLO inicializado com sucesso em {self.device}")
    
    def _detectar_device(self, force_cpu=False):
        """
        Detecta device disponível com fallback automático.
        
        Returns:
            torch.device: Device a usar (cuda, mps ou cpu)
        """
        if force_cpu:
            logger.info("CPU forçada via --force-cpu")
            return self._device_torch('cpu')
        
        try:
            import torch
            
            # Prioridade 1: GPU NVIDIA (CUDA)
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"GPU CUDA detectada: {device_name}")
                return self._device_torch('cuda:0')
            
            # Prioridade 2: GPU Apple (MPS)
            if torch.backends.mps.is_available():
                logger.info("GPU Metal Performance Shaders (macOS) detectada")
                return self._device_torch('mps')
            
            # Fallback: CPU
            logger.info("GPU não detectada; usando CPU")
            return self._device_torch('cpu')
        
        except ImportError:
            logger.error("torch não instalado; mode fallback para CPU")
            return self._device_torch('cpu')
    
    @staticmethod
    def _device_torch(device_str):
        """Cria torch.device com tratamento de erro."""
        try:
            import torch
            return torch.device(device_str)
        except Exception as e:
            logger.error(f"Erro ao criar device '{device_str}': {e}")
            return None
    
    def _carregar_modelo(self):
        """
        Carrega modelo YOLO no device detectado.
        Tenta usar ultralytics; fallback para DummyModel.
        """
        try:
            from ultralytics import YOLO
            
            logger.info(f"Carregando modelo de: {self.model_path}")
            self.model = YOLO(self.model_path)
            
            # Mover modelo para device
            if self.device:
                try:
                    self.model.to(self.device)
                    logger.info(f"Modelo movido para {self.device}")
                except Exception as e:
                    logger.warning(f"Erro ao mover modelo para device: {e}")
            
            self.usar_yolo_real = True
        
        except ImportError:
            logger.warning("ultralytics não instalado; usando DummyModel (sem detecções)")
            self.model = self._criar_dummy_model()
            self.usar_yolo_real = False
        
        except FileNotFoundError:
            logger.error(f"Arquivo de modelo não encontrado: {self.model_path}")
            raise
        
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            raise
    
    def track(self, frame, persist=True, classes=None, conf=0.4, verbose=False):
        """
        Executa tracking YOLO em frame.
        
        Args:
            frame: Imagem numpy (H, W, 3)
            persist (bool): Manter IDs entre frames
            classes (list): IDs de classes a detectar
            conf (float): Limiar de confiança
            verbose (bool): Log verboso
        
        Returns:
            list: Resultados [Results] do YOLO
        """
        if self.model is None:
            logger.error("Modelo não carregado; retornando vazio")
            return [self._criar_resultado_vazio()]
        
        try:
            results = self.model.track(
                frame,
                persist=persist,
                classes=classes,
                conf=conf,
                verbose=verbose
            )
            return results
        
        except Exception as e:
            logger.error(f"Erro durante tracking: {e}")
            return [self._criar_resultado_vazio()]
    
    def infer(self, frame, conf=0.4, verbose=False):
        """
        Executa inferência (sem tracking) em frame.
        
        Args:
            frame: Imagem numpy (H, W, 3)
            conf (float): Limiar de confiança
            verbose (bool): Log verboso
        
        Returns:
            list: Resultados [Results] do YOLO
        """
        if self.model is None:
            logger.error("Modelo não carregado; retornando vazio")
            return [self._criar_resultado_vazio()]
        
        try:
            results = self.model(frame, conf=conf, verbose=verbose)
            return results
        
        except Exception as e:
            logger.error(f"Erro durante inferência: {e}")
            return [self._criar_resultado_vazio()]
    
    @staticmethod
    def _criar_dummy_model():
        """Retorna modelo dummy que simula YOLO sem ultralytics."""
        class DummyModel:
            """Simula YOLO.track() sem detecções."""
            
            model_name = "dummy"
            
            def track(self, *args, **kwargs):
                return [DummyModel._criar_resultado_vazio()]
            
            def __call__(self, *args, **kwargs):
                return [DummyModel._criar_resultado_vazio()]
            
            def to(self, device):
                return self
            
            @staticmethod
            def _criar_resultado_vazio():
                class ResultadoVazio:
                    boxes = None
                return ResultadoVazio()
        
        return DummyModel()
    
    @staticmethod
    def _criar_resultado_vazio():
        """Retorna objeto Results vazio do YOLO."""
        class ResultadoVazio:
            boxes = None
        return ResultadoVazio()
    
    def __repr__(self):
        """String de representação."""
        return f"InferenceBackend(model={self.model_path}, device={self.device})"
 
 
# ============================================================================
# Funções helper para integração em main.py
# ============================================================================
 
def criar_backend_logger():
    """Configura logging para InferenceBackend."""
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
 
 
def testar_backend():
    """Teste rápido de funcionalidade (para debugging)."""
    import numpy as np
    
    print("\n=== Teste InferenceBackend ===\n")
    
    # Criar frame dummy
    frame_dummy = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Testar CPU
    print("1. Testando detecção de device...")
    try:
        backend = InferenceBackend('yolov8s.pt', force_cpu=True)
        print(f"   ✓ Backend criado: {backend}")
        print(f"   ✓ Device: {backend.device}")
    except Exception as e:
        print(f"   ✗ Erro: {e}")
        return
    
    # Testar track
    print("\n2. Testando track()...")
    try:
        results = backend.track(frame_dummy, persist=True, conf=0.4)
        print(f"   ✓ Track retornou {len(results)} resultado(s)")
        if results[0].boxes is not None:
            print(f"   ✓ Detecções: {len(results[0].boxes)}")
        else:
            print(f"   ✓ Sem detecções (esperado para frame vazio)")
    except Exception as e:
        print(f"   ✗ Erro: {e}")
        return
    
    print("\n✓ Teste concluído com sucesso!\n")
 
 
if __name__ == "__main__":
    criar_backend_logger()
    testar_backend()