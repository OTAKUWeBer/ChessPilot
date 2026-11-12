use super::{decode_boxes, preprocess_image, Predictor, RgbFrame};
use chesspilot_core::detection::Detection;
use ort::{
    session::Session,
    tensor::TensorElementType,
    value::{Tensor, ValueType},
};
use std::{
    path::{Path, PathBuf},
    sync::Mutex,
};
static RUNTIME: Mutex<Option<PathBuf>> = Mutex::new(None);

pub struct OnnxPredictor {
    session: Session,
}
impl OnnxPredictor {
    pub fn load(model: &Path, runtime: &Path) -> Result<Self, String> {
        let runtime = runtime
            .canonicalize()
            .map_err(|e| format!("ONNX Runtime is missing: {e}"))?;
        if !model.is_file() {
            return Err("Chess detection model is missing".into());
        }
        let mut initialized = RUNTIME
            .lock()
            .map_err(|_| "ONNX initialization lock failed")?;
        if initialized
            .as_ref()
            .is_some_and(|existing| *existing != runtime)
        {
            return Err("Restart the application before changing ONNX Runtime libraries".into());
        }
        // The binding may panic when loading an incompatible dynamic library.
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            if initialized.is_none() {
                ort::init_from(runtime.to_string_lossy())
                    .with_name("ChessPilot")
                    .commit()
                    .map_err(|e| e.to_string())?;
                *initialized = Some(runtime);
            }
            let session = Session::builder()
                .map_err(|e| e.to_string())?
                .commit_from_file(model)
                .map_err(|e| e.to_string())?;
            if session.inputs.len() != 1 || session.outputs.len() != 1 {
                return Err("Expected one model input and output".into());
            }
            if !matches!(&session.inputs[0].input_type,ValueType::Tensor{ty:TensorElementType::Float32,dimensions,..} if dimensions==&[1,3,640,640])
                || !matches!(&session.outputs[0].output_type,ValueType::Tensor{ty:TensorElementType::Float32,dimensions,..} if dimensions==&[1,300,6])
            {
                return Err("Model must use f32 input [1,3,640,640] and output [1,300,6]".into());
            }
            Ok(Self { session })
        }));
        result.unwrap_or_else(|_| Err("ONNX Runtime could not be initialized".into()))
    }
}
impl Predictor for OnnxPredictor {
    fn predict(&mut self, frame: &RgbFrame) -> Result<Vec<Detection>, String> {
        let (data, transform) = preprocess_image(frame)?;
        let tensor = Tensor::from_array(([1usize, 3, 640, 640], data.into_boxed_slice()))
            .map_err(|e| e.to_string())?;
        let inputs = ort::inputs![tensor].map_err(|e| e.to_string())?;
        let outputs = self.session.run(inputs).map_err(|e| e.to_string())?;
        let (shape, rows) = outputs[0]
            .try_extract_raw_tensor::<f32>()
            .map_err(|e| e.to_string())?;
        decode_boxes(rows, shape, transform)
    }
}
