"""
Dataset preparation module for LoRA fine-tuning
Creates training datasets in JSONL format from clinical data
"""
import json
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from utils.text_processor import ClinicalDataProcessor
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoRADatasetBuilder:
    """
    Class to build datasets for LoRA fine-tuning from clinical data
    """
    
    def __init__(self, output_dir: str = "datasets"):
        """
        Initialize the dataset builder
        
        :param output_dir: Directory to save the datasets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.processor = ClinicalDataProcessor()
    
    def create_clinical_qa_pair(self, context: str, question: str, answer: str) -> Dict[str, str]:
        """
        Create a QA pair in the format needed for fine-tuning
        
        :param context: Context information (patient notes, assessments, etc.)
        :param question: Question about the clinical context
        :param answer: Ideal answer for the question
        :return: Dictionary with input and output for fine-tuning
        """
        input_text = f"Context: {context}\n\nQuestion: {question}\n\nProvide a clinical response based on the context."
        
        return {
            "input": input_text,
            "output": answer
        }
    
    def create_behavioral_intervention_dataset(self, clinical_notes: List[str]) -> List[Dict[str, str]]:
        """
        Create a dataset focused on behavioral interventions from clinical notes
        
        :param clinical_notes: List of clinical notes/assessments
        :return: List of training examples for behavioral interventions
        """
        dataset = []
        
        for note in clinical_notes:
            # Extract relevant information from the clinical note
            metadata = self.processor.extract_metadata_from_text(note)
            
            # Create various QA pairs based on the note
            qa_pairs = [
                # Question about accommodations
                {
                    "context": note,
                    "question": "What accommodations would be appropriate for this patient?",
                    "answer": self._generate_accommodation_response(metadata, note)
                },
                # Question about behavioral interventions
                {
                    "context": note,
                    "question": "What behavioral interventions should be implemented?",
                    "answer": self._generate_behavioral_response(metadata, note)
                },
                # Question about sensory needs
                {
                    "context": note,
                    "question": "What are the patient's sensory needs?",
                    "answer": self._generate_sensory_response(metadata, note)
                },
                # General summary question
                {
                    "context": note,
                    "question": "Summarize this patient's profile and needs.",
                    "answer": self._generate_summary_response(metadata, note)
                }
            ]
            
            # Convert each QA pair to fine-tuning format
            for pair in qa_pairs:
                dataset.append(self.create_clinical_qa_pair(
                    pair["context"],
                    pair["question"],
                    pair["answer"]
                ))
        
        return dataset
    
    def _generate_accommodation_response(self, metadata: Dict[str, Any], context: str) -> str:
        """Generate accommodation response based on metadata and context"""
        response_parts = ["Based on the clinical assessment, the following accommodations are recommended:"]
        
        if "auditory" in metadata.get("sensory_flags", []):
            response_parts.append("• Provide noise-reducing headphones or ear defenders in noisy environments")
        
        if "visual" in metadata.get("sensory_flags", []):
            response_parts.append("• Offer dim lighting options or sunglasses for light sensitivity")
        
        if "tactile" in metadata.get("sensory_flags", []):
            response_parts.append("• Provide fidget tools or textured objects for tactile regulation")
        
        if "sensory seeking" in metadata.get("sensory_flags", []):
            response_parts.append("• Implement sensory breaks with proprioceptive activities")
        
        if "hyperactive" in metadata.get("behavioral_notes", []):
            response_parts.append("• Allow movement breaks or standing desk options")
        
        if "inattentive" in metadata.get("behavioral_notes", []):
            response_parts.append("• Use visual schedules and reminders to maintain focus")
        
        if len(response_parts) == 1:  # No specific accommodations identified
            response_parts.append("• Provide a calm, structured environment")
            response_parts.append("• Use clear, simple instructions")
            response_parts.append("• Allow extra processing time for complex tasks")
        
        return "\n".join(response_parts)
    
    def _generate_behavioral_response(self, metadata: Dict[str, Any], context: str) -> str:
        """Generate behavioral intervention response based on metadata and context"""
        response_parts = ["Recommended behavioral interventions include:"]
        
        if "aggressive" in metadata.get("behavioral_notes", []):
            response_parts.append("• Implement de-escalation strategies")
            response_parts.append("• Create a calm-down space with sensory supports")
        
        if "withdrawn" in metadata.get("behavioral_notes", []):
            response_parts.append("• Use gentle prompting and encouragement")
            response_parts.append("• Provide choices to increase engagement")
        
        if "impulsive" in metadata.get("behavioral_notes", []):
            response_parts.append("• Use self-monitoring tools and visual cues")
            response_parts.append("• Practice pause-and-think strategies")
        
        if "challenging behavior" in metadata.get("behavioral_notes", []):
            response_parts.append("• Implement positive behavior support plan")
            response_parts.append("• Use reinforcement for appropriate behaviors")
        
        if len(response_parts) == 1:  # No specific behaviors identified
            response_parts.append("• Use positive reinforcement for desired behaviors")
            response_parts.append("• Implement consistent routines and expectations")
            response_parts.append("• Provide clear feedback and consequences")
        
        return "\n".join(response_parts)
    
    def _generate_sensory_response(self, metadata: Dict[str, Any], context: str) -> str:
        """Generate sensory needs response based on metadata and context"""
        response_parts = ["This patient has the following sensory needs:"]
        
        sensory_flags = metadata.get("sensory_flags", [])
        
        if any(flag in sensory_flags for flag in ["hypersensitive", "sensitive", "noise sensitive"]):
            response_parts.append("• Hypersensitivity requiring environmental modifications")
        
        if "auditory" in sensory_flags:
            response_parts.append("• Auditory processing difficulties")
        
        if "tactile" in sensory_flags:
            response_parts.append("• Tactile sensitivity or seeking behaviors")
        
        if "visual" in sensory_flags:
            response_parts.append("• Visual processing challenges")
        
        if "sensory seeking" in sensory_flags:
            response_parts.append("• Requires increased sensory input for regulation")
        
        if "sensory avoiding" in sensory_flags:
            response_parts.append("• Avoids certain sensory experiences")
        
        if len(response_parts) == 1:  # No specific sensory flags
            response_parts.append("• Standard sensory processing")
            response_parts.append("• Monitor for sensory triggers during activities")
        
        return "\n".join(response_parts)
    
    def _generate_summary_response(self, metadata: Dict[str, Any], context: str) -> str:
        """Generate patient profile summary based on metadata and context"""
        response_parts = ["Patient Profile Summary:"]
        
        if metadata.get("date"):
            response_parts.append(f"• Assessment Date: {metadata['date']}")
        
        if metadata.get("therapist"):
            response_parts.append(f"• Conducted by: {metadata['therapist']}")
        
        if metadata.get("session_type"):
            response_parts.append(f"• Session Type: {metadata['session_type']}")
        
        if metadata.get("diagnosis_mentions"):
            response_parts.append(f"• Diagnosis: {', '.join(metadata['diagnosis_mentions'])}")
        
        sensory_flags = metadata.get("sensory_flags", [])
        if sensory_flags:
            response_parts.append(f"• Sensory Profile: {', '.join(sensory_flags)}")
        
        behavioral_notes = metadata.get("behavioral_notes", [])
        if behavioral_notes:
            response_parts.append(f"• Behavioral Notes: {', '.join(behavioral_notes)}")
        
        response_parts.append("\nClinical Recommendations:")
        response_parts.append("• Tailor interventions to the patient's specific profile")
        response_parts.append("• Monitor progress and adjust strategies as needed")
        
        return "\n".join(response_parts)
    
    def create_dataset_from_raw_clinical_notes(self, 
                                             clinical_notes: List[str], 
                                             output_file: str = "clinical_dataset.jsonl",
                                             dataset_type: str = "behavioral_interventions") -> str:
        """
        Create a complete training dataset from raw clinical notes
        
        :param clinical_notes: List of raw clinical notes/assessments
        :param output_file: Output file name for the dataset
        :param dataset_type: Type of dataset to create
        :return: Path to the created dataset file
        """
        if dataset_type == "behavioral_interventions":
            dataset = self.create_behavioral_intervention_dataset(clinical_notes)
        else:
            raise ValueError(f"Unknown dataset type: {dataset_type}")
        
        # Write to JSONL file
        output_path = self.output_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in dataset:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        logger.info(f"Created dataset with {len(dataset)} training examples in {output_path}")
        return str(output_path)
    
    def create_synthetic_clinical_dataset(self, num_samples: int = 100) -> List[Dict[str, str]]:
        """
        Create a synthetic clinical dataset for testing purposes
        
        :param num_samples: Number of samples to generate
        :return: List of training examples
        """
        dataset = []
        
        # Define common clinical scenarios
        patient_profiles = [
            {
                "profile": "8-year-old with ADHD and sensory processing issues",
                "symptoms": ["impulsive", "distracted", "auditory sensitive"],
                "interventions": ["behavioral chart", "sensory breaks", "noise reduction"]
            },
            {
                "profile": "10-year-old with autism spectrum disorder",
                "symptoms": ["repetitive behaviors", "sensory avoidant", "communication challenges"],
                "interventions": ["visual supports", "structured routine", "social stories"]
            },
            {
                "profile": "7-year-old with learning disabilities",
                "symptoms": ["frustration", "avoiding tasks", "low confidence"],
                "interventions": ["modified assignments", "positive reinforcement", "multisensory learning"]
            }
        ]
        
        questions_templates = [
            "What accommodations would benefit this patient?",
            "How should the classroom environment be modified?",
            "What behavioral interventions are appropriate?",
            "What are the student's sensory needs?",
            "How can learning be supported?",
            "What strategies promote independence?",
            "How can social skills be developed?",
            "What family involvement is recommended?"
        ]
        
        answer_templates = [
            "Based on the clinical profile, consider implementing {intervention} to address {symptom}.",
            "Environmental modifications such as {modification} would support this student's needs.",
            "A structured approach with {strategy} would be beneficial given the {profile}.",
            "Sensory accommodations including {accommodation} should be provided.",
            "Positive behavior support with {intervention} would help with {behavior}.",
        ]
        
        for i in range(num_samples):
            # Select random profile
            profile = random.choice(patient_profiles)
            
            # Select random question
            question = random.choice(questions_templates)
            
            # Generate answer based on profile
            answer_template = random.choice(answer_templates)
            answer = answer_template.format(
                intervention=random.choice(profile["interventions"]),
                symptom=random.choice(profile["symptoms"]),
                modification="environmental adjustments",
                strategy="evidence-based interventions",
                profile=profile["profile"],
                accommodation="sensory supports",
                behavior=random.choice(profile["symptoms"])
            )
            
            # Create context
            context = f"Patient Profile: {profile['profile']}. Key symptoms include: {', '.join(profile['symptoms'])}. Recommended interventions: {', '.join(profile['interventions'])}."
            
            # Add to dataset
            dataset.append(self.create_clinical_qa_pair(context, question, answer))
        
        return dataset
    
    def split_dataset(self, 
                     dataset: List[Dict[str, str]], 
                     train_ratio: float = 0.8, 
                     val_ratio: float = 0.15,
                     test_ratio: float = 0.05) -> Dict[str, List[Dict[str, str]]]:
        """
        Split dataset into train, validation, and test sets
        
        :param dataset: Complete dataset to split
        :param train_ratio: Proportion for training set
        :param val_ratio: Proportion for validation set
        :param test_ratio: Proportion for test set (should sum to 1.0)
        :return: Dictionary with train, val, test splits
        """
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 1e-6:
            raise ValueError("Ratios must sum to 1.0")
        
        # Shuffle dataset
        shuffled_dataset = dataset.copy()
        random.shuffle(shuffled_dataset)
        
        n = len(shuffled_dataset)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        splits = {
            "train": shuffled_dataset[:train_end],
            "validation": shuffled_dataset[train_end:val_end],
            "test": shuffled_dataset[val_end:]
        }
        
        logger.info(f"Dataset split: {len(splits['train'])} train, {len(splits['validation'])} validation, {len(splits['test'])} test")
        
        return splits
    
    def save_dataset_splits(self, 
                           splits: Dict[str, List[Dict[str, str]]], 
                           base_filename: str = "clinical_dataset") -> Dict[str, str]:
        """
        Save dataset splits to separate files
        
        :param splits: Dictionary with train, val, test splits
        :param base_filename: Base filename for the splits
        :return: Dictionary mapping split names to file paths
        """
        file_paths = {}
        
        for split_name, split_data in splits.items():
            filename = f"{base_filename}_{split_name}.jsonl"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                for item in split_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
            file_paths[split_name] = str(filepath)
            logger.info(f"Saved {split_name} split with {len(split_data)} examples to {filepath}")
        
        return file_paths
    
    def create_complete_training_pipeline(self, 
                                        clinical_notes: List[str] = None,
                                        num_synthetic: int = 100,
                                        output_base: str = "clinical_lora_dataset") -> Dict[str, str]:
        """
        Complete pipeline for creating a training dataset
        
        :param clinical_notes: List of real clinical notes (optional)
        :param num_synthetic: Number of synthetic examples to include
        :param output_base: Base name for output files
        :return: Dictionary mapping split names to file paths
        """
        # Create dataset from clinical notes if provided
        if clinical_notes:
            real_dataset = self.create_behavioral_intervention_dataset(clinical_notes)
        else:
            real_dataset = []
        
        # Create synthetic dataset
        synthetic_dataset = self.create_synthetic_clinical_dataset(num_synthetic)
        
        # Combine datasets
        full_dataset = real_dataset + synthetic_dataset
        
        # Split the dataset
        splits = self.split_dataset(full_dataset)
        
        # Save splits to files
        file_paths = self.save_dataset_splits(splits, output_base)
        
        logger.info(f"Training pipeline completed. Dataset statistics:")
        logger.info(f"  - Real examples: {len(real_dataset)}")
        logger.info(f"  - Synthetic examples: {num_synthetic}")
        logger.info(f"  - Total examples: {len(full_dataset)}")
        
        return file_paths


# Example usage function
def example_usage():
    """
    Example of how to use the LoRADatasetBuilder
    """
    builder = LoRADatasetBuilder()
    
    # Example clinical notes
    clinical_notes = [
        """
        Assessment Report: Lucas Silva
        Date: 2023-05-15
        Age: 8 years
        Diagnosis: Learning difficulties, Auditory hypersensitivity
        
        Lucas demonstrates challenges with reading comprehension and exhibits 
        hypersensitivity to loud noises in the classroom. When exposed to 
        auditory stimuli like fire alarms or construction noise, he covers 
        his ears and becomes visibly distressed.
        
        Recommendation: Provide noise-canceling headphones during reading 
        activities and implement a sensory break schedule every 30 minutes.
        """,
        """
        Progress Report: Maria Santos
        Date: 2023-06-20
        Age: 10 years
        Diagnosis: Autism Spectrum Disorder
        
        Maria continues to benefit from visual supports and structured routine. 
        She responds well to social stories and has shown improvement in 
        requesting breaks when feeling overwhelmed.
        
        Next steps: Introduce peer interaction activities with structured support.
        """,
        """
        Initial Evaluation: João Oliveira
        Date: 2023-07-10
        Age: 7 years
        Diagnosis: Attention Deficit Hyperactivity Disorder
        
        João shows impulsivity and difficulty focusing during seated work. 
        He benefits from movement breaks and positive reinforcement systems. 
        Handwriting remains challenging but improving with multisensory approaches.
        
        Recommendations: Implement fidget tools and token economy system.
        """
    ]
    
    # Create complete training dataset
    file_paths = builder.create_complete_training_pipeline(
        clinical_notes=clinical_notes,
        num_synthetic=50,  # Add 50 synthetic examples to augment real data
        output_base="clinical_behavioral_interventions"
    )
    
    print("Created dataset files:")
    for split_name, path in file_paths.items():
        print(f"  {split_name}: {path}")
    
    # Show example of first training example
    if clinical_notes:
        first_qa = builder.create_behavioral_intervention_dataset(clinical_notes[:1])[0]
        print(f"\nExample training pair:")
        print(f"Input: {first_qa['input'][:200]}...")
        print(f"Output: {first_qa['output'][:100]}...")


if __name__ == "__main__":
    example_usage()