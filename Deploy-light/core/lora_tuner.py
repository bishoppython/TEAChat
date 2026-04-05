"""
LoRA fine-tuning module for clinical psychology models
Uses Hugging Face transformers and PEFT library
"""
import os
import logging
from typing import Optional, Dict, Any, List
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import (
    get_peft_model, 
    LoraConfig, 
    TaskType,
    prepare_model_for_kbit_training
)
from trl import SFTTrainer
from datasets import Dataset
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinicalLoRATuner:
    """
    Class to handle LoRA fine-tuning for clinical psychology applications
    """
    
    def __init__(self, 
                 base_model_name: str = "microsoft/DialoGPT-medium",
                 device: str = None):
        """
        Initialize the LoRA tuner
        
        :param base_model_name: Name of the base model to fine-tune
        :param device: Device to use for training ('cuda', 'cpu', or None for auto)
        """
        self.base_model_name = base_model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        
        # Add padding token if not present
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            load_in_8bit=True,  # Use 8-bit quantization to save memory
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            device_map="auto" if self.device == "cuda" else None
        )
        
        # Prepare model for k-bit training
        self.model = prepare_model_for_kbit_training(self.model)
    
    def prepare_peft_model(self,
                          r: int = 16,
                          alpha: int = 32,
                          dropout: float = 0.05,
                          target_modules: List[str] = None) -> None:
        """
        Prepare the model with LoRA configuration
        
        :param r: LoRA rank
        :param alpha: LoRA alpha parameter
        :param dropout: Dropout rate for LoRA layers
        :param target_modules: Specific modules to apply LoRA to (if None, uses defaults)
        """
        if target_modules is None:
            # Default target modules for common models
            target_modules = ["q_proj", "v_proj", "k_proj", "out_proj", "fc_in", "fc_out", "wte"]
        
        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=r,
            lora_alpha=alpha,
            lora_dropout=dropout,
            target_modules=target_modules
        )
        
        self.model = get_peft_model(self.model, peft_config)
        self.model.print_trainable_parameters()
    
    def load_dataset_from_jsonl(self, file_path: str, max_samples: Optional[int] = None) -> Dataset:
        """
        Load dataset from JSONL file
        
        :param file_path: Path to the JSONL dataset file
        :param max_samples: Maximum number of samples to load (for testing)
        :return: HuggingFace Dataset
        """
        data = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if max_samples and i >= max_samples:
                    break
                
                item = json.loads(line.strip())
                data.append(item)
        
        # Convert to HuggingFace format
        hf_dataset = Dataset.from_list(data)
        return hf_dataset
    
    def format_training_examples(self, examples: List[Dict[str, str]]) -> List[str]:
        """
        Format training examples for language model training
        
        :param examples: List of dictionaries with 'input' and 'output' keys
        :return: List of formatted training texts
        """
        formatted_texts = []
        
        for example in examples:
            input_text = example['input']
            output_text = example['output']
            
            # Format as conversation or instruction-following format
            formatted = f"### Instruction:\n{input_text}\n\n### Response:\n{output_text}</s>"
            formatted_texts.append(formatted)
        
        return formatted_texts
    
    def tokenize_function(self, examples: Dict[str, List[str]]) -> Dict[str, List[int]]:
        """
        Tokenize function for the dataset
        """
        # Combine input and output for tokenization
        texts = [item['input'] + " " + item['output'] for item in examples]
        
        # Tokenize the texts
        tokenized = self.tokenizer(
            texts,
            truncation=True,
            padding=True,
            max_length=512,  # Adjust based on model's max length
            return_tensors="pt"
        )
        
        # For causal LM, labels are the same as input_ids
        tokenized["labels"] = tokenized["input_ids"].clone()
        
        return tokenized
    
    def prepare_training_dataset(self, dataset_path: str, max_samples: Optional[int] = None) -> Dataset:
        """
        Prepare the training dataset
        
        :param dataset_path: Path to the training dataset
        :param max_samples: Maximum number of samples to use (for testing)
        :return: Prepared training dataset
        """
        # Load raw dataset
        raw_dataset = self.load_dataset_from_jsonl(dataset_path, max_samples)
        
        # Apply tokenization
        tokenized_dataset = raw_dataset.map(
            self.tokenize_function,
            batched=True,
            remove_columns=raw_dataset.column_names
        )
        
        return tokenized_dataset
    
    def train(self,
              train_dataset_path: str,
              validation_dataset_path: str = None,
              output_dir: str = "./lora_clinical_model",
              num_train_epochs: int = 3,
              per_device_train_batch_size: int = 4,
              per_device_eval_batch_size: int = 4,
              gradient_accumulation_steps: int = 8,
              learning_rate: float = 2e-4,
              warmup_steps: int = 100,
              save_steps: int = 500,
              eval_steps: int = 500,
              logging_steps: int = 10,
              max_samples: Optional[int] = None) -> str:
        """
        Train the LoRA model
        
        :param train_dataset_path: Path to training dataset
        :param validation_dataset_path: Path to validation dataset (optional)
        :param output_dir: Directory to save the trained model
        :param num_train_epochs: Number of training epochs
        :param per_device_train_batch_size: Batch size for training
        :param per_device_eval_batch_size: Batch size for evaluation
        :param gradient_accumulation_steps: Number of steps for gradient accumulation
        :param learning_rate: Learning rate
        :param warmup_steps: Number of warmup steps
        :param save_steps: Steps between model saves
        :param eval_steps: Steps between evaluations
        :param logging_steps: Steps between loggings
        :param max_samples: Maximum samples to use for testing
        :return: Path to saved model
        """
        # Prepare datasets
        train_dataset = self.prepare_training_dataset(train_dataset_path, max_samples)
        
        if validation_dataset_path:
            eval_dataset = self.prepare_training_dataset(validation_dataset_path, max_samples)
        else:
            eval_dataset = None
        
        # Define training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            overwrite_output_dir=True,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size,
            per_device_eval_batch_size=per_device_eval_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            evaluation_strategy="steps" if eval_dataset else "no",
            eval_steps=eval_steps if eval_dataset else None,
            save_strategy="steps",
            save_steps=save_steps,
            logging_dir=f"{output_dir}/logs",
            logging_steps=logging_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            fp16=True if self.device == "cuda" else False,  # Mixed precision training
            load_best_model_at_end=True if eval_dataset else False,
            metric_for_best_model="eval_loss" if eval_dataset else None,
            greater_is_better=False,
            save_total_limit=3,  # Only keep 3 latest checkpoints
            prediction_loss_only=True,
            remove_unused_columns=False,
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False  # Not using masked language modeling for causal LM
            ),
        )
        
        # Start training
        logger.info("Starting training...")
        trainer.train()
        
        # Save the model
        final_model_path = f"{output_dir}/final_model"
        trainer.save_model(final_model_path)
        self.tokenizer.save_pretrained(final_model_path)
        
        logger.info(f"Model saved to {final_model_path}")
        
        return final_model_path
    
    def train_with_sft(self,
                      train_dataset_path: str,
                      validation_dataset_path: str = None,
                      output_dir: str = "./lora_clinical_model_sft",
                      max_seq_length: int = 512,
                      num_train_epochs: int = 3,
                      per_device_train_batch_size: int = 4,
                      gradient_accumulation_steps: int = 8,
                      learning_rate: float = 2e-4,
                      max_samples: Optional[int] = None) -> str:
        """
        Train the model using SFT (Supervised Fine-Tuning) trainer
        This is often more efficient for instruction-following tasks
        
        :param train_dataset_path: Path to training dataset
        :param validation_dataset_path: Path to validation dataset (optional)
        :param output_dir: Directory to save the trained model
        :param max_seq_length: Maximum sequence length
        :param num_train_epochs: Number of training epochs
        :param per_device_train_batch_size: Batch size for training
        :param gradient_accumulation_steps: Number of steps for gradient accumulation
        :param learning_rate: Learning rate
        :param max_samples: Maximum samples to use for testing
        :return: Path to saved model
        """
        # Load datasets
        train_dataset = self.load_dataset_from_jsonl(train_dataset_path, max_samples)
        eval_dataset = None
        if validation_dataset_path:
            eval_dataset = self.load_dataset_from_jsonl(validation_dataset_path, max_samples)
        
        # Initialize SFT trainer
        trainer = SFTTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            dataset_text_field="input",  # Field containing the text to tokenize
            max_seq_length=max_seq_length,
            dataset_num_proc=2,
            packing=False,  # Don't pack multiple examples into one sequence
            args=TrainingArguments(
                output_dir=output_dir,
                per_device_train_batch_size=per_device_train_batch_size,
                gradient_accumulation_steps=gradient_accumulation_steps,
                warmup_steps=100,
                num_train_epochs=num_train_epochs,
                learning_rate=learning_rate,
                fp16=True if self.device == "cuda" else False,
                logging_steps=10,
                save_strategy="epoch",
                evaluation_strategy="epoch" if eval_dataset else "no",
                remove_unused_columns=False,
                report_to=None,  # Disable reporting to save resources
            ),
        )
        
        # Start training
        logger.info("Starting SFT training...")
        trainer.train()
        
        # Save the model
        final_model_path = f"{output_dir}/final_model"
        trainer.save_model(final_model_path)
        self.tokenizer.save_pretrained(final_model_path)
        
        logger.info(f"SFT model saved to {final_model_path}")
        
        return final_model_path
    
    def generate_response(self, 
                         prompt: str, 
                         max_length: int = 200,
                         temperature: float = 0.7,
                         do_sample: bool = True) -> str:
        """
        Generate a response using the trained model
        
        :param prompt: Input prompt
        :param max_length: Maximum length of generated text
        :param temperature: Sampling temperature
        :param do_sample: Whether to use sampling or greedy decoding
        :return: Generated response
        """
        # Tokenize the input
        inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
        
        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=len(inputs[0]) + max_length,
                temperature=temperature,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode the output
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract just the generated part (remove the original prompt)
        response = response[len(prompt):].strip()
        
        return response


# Example usage function
def example_usage():
    """
    Example of how to use the ClinicalLoRATuner
    """
    # Initialize the tuner
    tuner = ClinicalLoRATuner(base_model_name="microsoft/DialoGPT-medium")
    
    # Prepare PEFT model with LoRA configuration
    tuner.prepare_peft_model(
        r=16,      # LoRA rank
        alpha=32,  # LoRA alpha
        dropout=0.05  # Dropout rate
    )
    
    # Example: Train the model (this would need actual dataset files)
    # trainer.train(
    #     train_dataset_path="path/to/train_dataset.jsonl",
    #     validation_dataset_path="path/to/validation_dataset.jsonl",
    #     output_dir="./clinical_lora_model",
    #     num_train_epochs=3,
    #     per_device_train_batch_size=4
    # )
    
    # Example response generation (with a dummy prompt since model isn't trained)
    sample_prompt = "### Instruction:\nContext: Patient shows hypersensitivity to auditory stimuli\n\nQuestion: What accommodations should be made?\n\n### Response:\n"
    
    print("Sample response generation (with untrained model):")
    print("Prompt:", sample_prompt)
    
    # Note: Since the model hasn't been trained, this will generate random text
    # In practice, you would load a trained model for meaningful responses
    try:
        response = tuner.generate_response(sample_prompt, max_length=100)
        print("Response:", response)
    except Exception as e:
        print(f"Could not generate response: {e}")
    
    print("\nFor actual training, you would:")
    print("1. Prepare your JSONL dataset using the dataset_builder module")
    print("2. Call tuner.train() with your dataset paths")
    print("3. Use the trained model for inference")


if __name__ == "__main__":
    example_usage()