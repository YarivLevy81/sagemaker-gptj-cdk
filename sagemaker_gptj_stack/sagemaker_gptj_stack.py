from aws_cdk import (
    Stack,
    aws_sagemaker_alpha as sagemaker,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_iam as iam,
)
from constructs import Construct


class SagemakerGPTJStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket = s3.Bucket.from_bucket_name(
            self, "Bucket", "sagemaker-studio-emje97blvoj"
        )
        model_data = sagemaker.ModelData.from_bucket(bucket, "gpt-j/model.tar.gz")
        repository = ecr.Repository.from_repository_arn(
            self,
            "EcrRepo",
            repository_arn="arn:aws:ecr:us-west-2:763104351884:repository"
            "/huggingface-pytorch-inference",
        )
        image = sagemaker.ContainerImage.from_ecr_repository(
            repository, "1.9.1-transformers4.12.3-gpu-py38-cu111" "-ubuntu20.04"
        )

        model = sagemaker.Model(
            self,
            "PrimaryContainerModel",
            containers=[
                sagemaker.ContainerDefinition(image=image, model_data=model_data)
            ],
            role=iam.Role(
                scope=self,
                id="ModelRole",
                role_name="ModelRole",
                inline_policies={
                    "ModelPolicy": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                actions=[
                                    "sagemaker:*",
                                    "s3:Get*",
                                    "s3:List*",
                                    "s3:Put*",
                                    "ecr:GetAuthorizationToken",
                                    "ecr:BatchCheckLayerAvailability",
                                    "ecr:GetDownloadUrlForLayer",
                                    "ecr:BatchGetImage",
                                ],
                                resources=["*"],
                            )
                        ]
                    )
                },
                assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            ),
        )

        variant_name = "my-variant"
        endpoint_config = sagemaker.EndpointConfig(
            self,
            "EndpointConfig",
            instance_production_variants=[
                sagemaker.InstanceProductionVariantProps(
                    model=model,
                    variant_name=variant_name,
                    instance_type=sagemaker.InstanceType(
                        "ml.g4dn.xlarge",
                    ),
                )
            ],
        )

        endpoint = sagemaker.Endpoint(self, "Endpoint", endpoint_config=endpoint_config)
        production_variant = endpoint.find_instance_production_variant(variant_name)
        instance_count = production_variant.auto_scale_instance_count(max_capacity=3)
        instance_count.scale_on_invocations("LimitRPS", max_requests_per_second=30)
