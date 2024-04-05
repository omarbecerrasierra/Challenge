from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    Stack,
    Duration,
    CfnOutput
)
from aws_cdk import aws_iam as iam
from constructs import Construct
import os, subprocess 
from dotenv import load_dotenv
load_dotenv()
class CdkProyectStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Define una VPC
        vpc = ec2.Vpc(self, "MyVPC",
                      max_azs=3,
                      nat_gateways=1,
                      vpc_name="MyVPC")

        db_instance = rds.DatabaseInstance(self, "MyDatabase",
                                            # configuración de la instancia
                                            credentials=rds.Credentials.from_generated_secret("administrador"),
                                            engine=rds.DatabaseInstanceEngine.mysql(
                                                        version=rds.MysqlEngineVersion.VER_8_0
                                                    ),
                                            database_name="mydatabase",
                                            vpc= vpc,
                                            vpc_subnets= ec2.SubnetSelection(
                                                subnet_type= ec2.SubnetType.PUBLIC,
                                            ),
                                            instance_type= ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE3,
                                                                            ec2.InstanceSize.MICRO),                                            allocated_storage= 80,
                                            deletion_protection= False,
                                            publicly_accessible= True,
                                            port= 3306,
                                    
                                   )

        def create_dependencies_layer(self, project_name, function_name: str) -> _lambda.LayerVersion:
            requirements_file = "layer/requirements.txt"
            output_dir = f".build/app"

            if not os.environ.get("SKIP_PIP"):
                subprocess.check_call(f"pip3 install -r {requirements_file} -t {output_dir}/python".split())

            layer_id = f"{project_name}-{function_name}-dependencies"
            layer_code = _lambda.Code.from_asset(output_dir) 

            my_layer = _lambda.LayerVersion(
                self,
                layer_id,
                code=layer_code
            )

            return my_layer
        
        # Crea una capa de dependencias
        layer = create_dependencies_layer(self, "cdk_proyect",  "app")
        # load AWSCDKPandas-Python310 of AWS layers
        layer_arn = os.environ.get("LAYER_ARN")

        # Crear una capa de Lambda a partir del ARN
        pandas_layer = _lambda.LayerVersion.from_layer_version_arn(
            self, "PandasLayer",
            layer_version_arn=layer_arn
        )

            # Crea una función Lambda para ejecutar FastAPI
        lambda_function = _lambda.Function(self, "MyFunction",
                                            runtime=_lambda.Runtime.PYTHON_3_10,
                                            handler="app.handler",
                                            code=_lambda.Code.from_asset("lambda"),
                                            vpc=vpc,
                                            environment={
                                                "DB_HOST": db_instance.db_instance_endpoint_address,
                                                "DB_NAME": "mydatabase",
                                                "DB_USER": "administrador",
                                                # Ajuste aquí: usar secret_value_from_json para obtener la contraseña
                                                "DB_PASSWORD_ARN": db_instance.secret.secret_arn,  # Pasa el ARN en lugar del valor
                                                "DB_PORT": "3306"
                                            },
                                            layers=[layer, pandas_layer],
                                            memory_size=1024,
                                            timeout=  Duration.seconds(30)

        )


        # Crea una política que permita acceder a Secrets Manager
        secrets_policy = iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[os.environ.get('RESOURCE_ARN')],  # Asegúrate de ajustar este ARN al de tu secreto específico
            effect=iam.Effect.ALLOW
        )

        # Adjunta la política al rol de la función Lambda
        lambda_function.add_to_role_policy(secrets_policy)


        # Crear una Function URL para la función Lambda
        function_url = lambda_function.add_function_url(
            auth_type=_lambda.FunctionUrlAuthType.NONE,  # Para demostración; considera usar AWS_IAM para producción
            cors=_lambda.FunctionUrlCorsOptions(
                allowed_origins=["*"],  # Ajusta según sea necesario para tu caso de uso
                allowed_methods=[_lambda.HttpMethod.GET, _lambda.HttpMethod.POST],  # Ajusta según los métodos que tu API necesita
            )
        )

        # Imprime la URL en la salida del despliegue de CDK
        CfnOutput(self, "FunctionUrl", value=function_url.url)

        # Configura el Amazon API Gateway
        api = apigateway.LambdaRestApi(self, "MyApi",
                                       handler=lambda_function,
                                       proxy=True,
        )
        # call the root resource
        api.root.add_method("GET")

        # Define a resource and method for `create_data`
        create_data_resource = api.root.add_resource("create_data")
        create_data_resource.add_method("POST")

        # Define a resource and method for `view_summary`
        view_summary_resource = api.root.add_resource("view_summary")
        view_summary_resource.add_method("GET")

        # Define a resource and method for `create_view`
        create_view_resource = api.root.add_resource("create_view")
        create_view_resource.add_method("POST")